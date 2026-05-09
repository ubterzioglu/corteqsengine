"""
Elasticsearch Service
Full-text search and indexing for knowledge nodes
"""

import os
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from elasticsearch import AsyncElasticsearch

ELASTICSEARCH_CLOUD_ID = os.environ.get("ELASTICSEARCH_CLOUD_ID")
ELASTICSEARCH_API_KEY = os.environ.get("ELASTICSEARCH_API_KEY")

INDEX_NAME = "corteqs_knowledge"


class ElasticsearchService:
    def __init__(self):
        self.client = None
        self.is_configured = bool(
            ELASTICSEARCH_CLOUD_ID and ELASTICSEARCH_API_KEY and
            ELASTICSEARCH_CLOUD_ID != "placeholder" and ELASTICSEARCH_API_KEY != "placeholder"
        )
    
    async def connect(self):
        """Initialize Elasticsearch connection"""
        if not self.is_configured:
            return
        
        try:
            self.client = AsyncElasticsearch(
                cloud_id=ELASTICSEARCH_CLOUD_ID,
                api_key=ELASTICSEARCH_API_KEY
            )
            # Verify connectivity
            info = await self.client.info()
            print(f"Elasticsearch connected: {info['cluster_name']}")
            
            # Create index if not exists
            await self._ensure_index()
        except Exception as e:
            print(f"Elasticsearch connection error: {e}")
            self.client = None
    
    async def close(self):
        """Close Elasticsearch connection"""
        if self.client:
            await self.client.close()
    
    async def _ensure_index(self):
        """Create the knowledge index with proper mappings"""
        if not self.client:
            return
        
        try:
            exists = await self.client.indices.exists(index=INDEX_NAME)
            if not exists:
                mappings = {
                    "properties": {
                        "node_id": {"type": "keyword"},
                        "user_id": {"type": "keyword"},
                        "node_type": {"type": "keyword"},
                        "title": {
                            "type": "text",
                            "analyzer": "standard",
                            "fields": {
                                "keyword": {"type": "keyword"}
                            }
                        },
                        "content": {
                            "type": "text",
                            "analyzer": "standard"
                        },
                        "source_type": {"type": "keyword"},
                        "source_id": {"type": "keyword"},
                        "tags": {"type": "keyword"},
                        "metadata": {"type": "object", "enabled": False},
                        "created_at": {"type": "date"},
                        "updated_at": {"type": "date"}
                    }
                }
                
                settings = {
                    "number_of_shards": 1,
                    "number_of_replicas": 1,
                    "analysis": {
                        "analyzer": {
                            "autocomplete": {
                                "type": "custom",
                                "tokenizer": "standard",
                                "filter": ["lowercase", "autocomplete_filter"]
                            }
                        },
                        "filter": {
                            "autocomplete_filter": {
                                "type": "edge_ngram",
                                "min_gram": 2,
                                "max_gram": 20
                            }
                        }
                    }
                }
                
                await self.client.indices.create(
                    index=INDEX_NAME,
                    body={"mappings": mappings, "settings": settings}
                )
                print(f"Created Elasticsearch index: {INDEX_NAME}")
        except Exception as e:
            print(f"Elasticsearch index creation error: {e}")
    
    async def index_node(
        self,
        node_id: str,
        user_id: str,
        node_type: str,
        title: str,
        content: Optional[str] = None,
        source_type: Optional[str] = None,
        source_id: Optional[str] = None,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Index a knowledge node for search"""
        if not self.client:
            return False
        
        doc = {
            "node_id": node_id,
            "user_id": user_id,
            "node_type": node_type,
            "title": title,
            "content": content or "",
            "source_type": source_type,
            "source_id": source_id,
            "tags": tags or [],
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            await self.client.index(
                index=INDEX_NAME,
                id=node_id,
                body=doc
            )
            return True
        except Exception as e:
            print(f"Elasticsearch index error: {e}")
            return False
    
    async def search(
        self,
        user_id: str,
        query: str,
        node_type: Optional[str] = None,
        source_type: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Full-text search across knowledge nodes"""
        if not self.client:
            return {"results": [], "total": 0}
        
        # Build query
        must = [{"term": {"user_id": user_id}}]
        
        if node_type:
            must.append({"term": {"node_type": node_type}})
        
        if source_type:
            must.append({"term": {"source_type": source_type}})
        
        search_query = {
            "bool": {
                "must": must,
                "should": [
                    {
                        "multi_match": {
                            "query": query,
                            "fields": ["title^3", "content", "tags^2"],
                            "type": "best_fields",
                            "fuzziness": "AUTO"
                        }
                    }
                ],
                "minimum_should_match": 1
            }
        }
        
        try:
            response = await self.client.search(
                index=INDEX_NAME,
                body={
                    "query": search_query,
                    "from": offset,
                    "size": limit,
                    "highlight": {
                        "fields": {
                            "title": {},
                            "content": {"fragment_size": 150, "number_of_fragments": 3}
                        }
                    },
                    "sort": [
                        "_score",
                        {"updated_at": {"order": "desc"}}
                    ]
                }
            )
            
            results = []
            for hit in response["hits"]["hits"]:
                result = hit["_source"]
                result["score"] = hit["_score"]
                result["highlights"] = hit.get("highlight", {})
                results.append(result)
            
            return {
                "results": results,
                "total": response["hits"]["total"]["value"],
                "query": query
            }
        except Exception as e:
            print(f"Elasticsearch search error: {e}")
            return {"results": [], "total": 0, "error": str(e)}
    
    async def autocomplete(
        self,
        user_id: str,
        prefix: str,
        limit: int = 10
    ) -> List[str]:
        """Autocomplete suggestions based on titles"""
        if not self.client:
            return []
        
        query = {
            "bool": {
                "must": [
                    {"term": {"user_id": user_id}},
                    {"prefix": {"title.keyword": {"value": prefix, "case_insensitive": True}}}
                ]
            }
        }
        
        try:
            response = await self.client.search(
                index=INDEX_NAME,
                body={
                    "query": query,
                    "size": limit,
                    "_source": ["title"]
                }
            )
            
            return [hit["_source"]["title"] for hit in response["hits"]["hits"]]
        except Exception as e:
            print(f"Elasticsearch autocomplete error: {e}")
            return []
    
    async def delete_node(self, node_id: str) -> bool:
        """Delete a node from the index"""
        if not self.client:
            return False
        
        try:
            await self.client.delete(index=INDEX_NAME, id=node_id)
            return True
        except Exception as e:
            print(f"Elasticsearch delete error: {e}")
            return False
    
    async def bulk_index(self, nodes: List[Dict[str, Any]]) -> int:
        """Bulk index multiple nodes"""
        if not self.client or not nodes:
            return 0
        
        from elasticsearch.helpers import async_bulk
        
        actions = []
        for node in nodes:
            actions.append({
                "_index": INDEX_NAME,
                "_id": node["node_id"],
                "_source": {
                    "node_id": node["node_id"],
                    "user_id": node["user_id"],
                    "node_type": node.get("node_type", "document"),
                    "title": node.get("title", ""),
                    "content": node.get("content", ""),
                    "source_type": node.get("source_type"),
                    "source_id": node.get("source_id"),
                    "tags": node.get("tags", []),
                    "metadata": node.get("metadata", {}),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            })
        
        try:
            success, _ = await async_bulk(self.client, actions)
            return success
        except Exception as e:
            print(f"Elasticsearch bulk index error: {e}")
            return 0
    
    async def get_stats(self, user_id: str) -> Dict[str, Any]:
        """Get search statistics for user"""
        if not self.client:
            return {}
        
        try:
            # Count by type
            response = await self.client.search(
                index=INDEX_NAME,
                body={
                    "query": {"term": {"user_id": user_id}},
                    "size": 0,
                    "aggs": {
                        "by_type": {"terms": {"field": "node_type"}},
                        "by_source": {"terms": {"field": "source_type"}}
                    }
                }
            )
            
            return {
                "total_indexed": response["hits"]["total"]["value"],
                "by_type": {
                    b["key"]: b["doc_count"] 
                    for b in response["aggregations"]["by_type"]["buckets"]
                },
                "by_source": {
                    b["key"]: b["doc_count"] 
                    for b in response["aggregations"]["by_source"]["buckets"]
                }
            }
        except Exception as e:
            print(f"Elasticsearch stats error: {e}")
            return {}
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test Elasticsearch connection"""
        if not self.is_configured:
            return {"connected": False, "error": "Elasticsearch not configured"}
        
        try:
            if not self.client:
                await self.connect()
            
            if self.client:
                info = await self.client.info()
                return {
                    "connected": True,
                    "cluster_name": info["cluster_name"],
                    "version": info["version"]["number"]
                }
            return {"connected": False, "error": "Client not initialized"}
        except Exception as e:
            return {"connected": False, "error": str(e)}


# Singleton instance
elasticsearch_service = ElasticsearchService()
