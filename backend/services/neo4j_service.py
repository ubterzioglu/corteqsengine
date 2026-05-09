"""
Neo4j Graph Database Service
Manages Knowledge Graph with Neo4j for efficient graph operations
"""

import os
from typing import List, Dict, Any, Optional
from neo4j import AsyncGraphDatabase, basic_auth

NEO4J_URI = os.environ.get("NEO4J_URI")
NEO4J_USER = os.environ.get("NEO4J_USER") or os.environ.get("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")
NEO4J_DATABASE = os.environ.get("NEO4J_DATABASE", "neo4j")


class Neo4jService:
    def __init__(self):
        self.driver = None
        self.active_uri = None
        self.is_configured = bool(
            NEO4J_URI and NEO4J_PASSWORD and 
            NEO4J_URI != "placeholder" and NEO4J_PASSWORD != "placeholder"
        )

    def _candidate_uris(self) -> List[str]:
        """Try stricter TLS first, then fallback to self-signed variants."""
        if not NEO4J_URI:
            return []

        candidates = [NEO4J_URI]
        if NEO4J_URI.startswith("neo4j+s://"):
            candidates.extend([
                NEO4J_URI.replace("neo4j+s://", "neo4j+ssc://", 1),
                NEO4J_URI.replace("neo4j+s://", "bolt+ssc://", 1),
            ])
        elif NEO4J_URI.startswith("neo4j://"):
            candidates.extend([
                NEO4J_URI.replace("neo4j://", "neo4j+ssc://", 1),
                NEO4J_URI.replace("neo4j://", "bolt+ssc://", 1),
            ])

        seen = set()
        ordered = []
        for candidate in candidates:
            if candidate not in seen:
                ordered.append(candidate)
                seen.add(candidate)
        return ordered
    
    async def connect(self):
        """Initialize Neo4j connection"""
        if not self.is_configured:
            return
        
        last_error = None
        for candidate_uri in self._candidate_uris():
            driver = AsyncGraphDatabase.driver(
                candidate_uri,
                auth=basic_auth(NEO4J_USER, NEO4J_PASSWORD)
            )
            try:
                await driver.verify_connectivity()
                self.driver = driver
                self.active_uri = candidate_uri
                print(f"Neo4j connected successfully via {candidate_uri}")
                return
            except Exception as e:
                last_error = e
                await driver.close()
        
        print(f"Neo4j connection error: {last_error}")
        self.driver = None
        self.active_uri = None
    
    async def close(self):
        """Close Neo4j connection"""
        if self.driver:
            await self.driver.close()
    
    async def create_node(
        self, 
        node_id: str,
        node_type: str, 
        title: str, 
        content: Optional[str] = None,
        metadata: Dict[str, Any] = None,
        user_id: str = None
    ) -> Optional[Dict[str, Any]]:
        """Create a node in the knowledge graph"""
        if not self.driver:
            return None

        # Simpler query without APOC
        simple_query = """
        MERGE (n:KnowledgeNode {node_id: $node_id})
        SET n.type = $node_type,
            n.title = $title,
            n.content = $content,
            n.user_id = $user_id,
            n.created_at = datetime(),
            n.updated_at = datetime()
        RETURN n
        """
        
        try:
            async with self.driver.session(database=NEO4J_DATABASE) as session:
                result = await session.run(
                    simple_query,
                    node_id=node_id,
                    node_type=node_type,
                    title=title,
                    content=content,
                    user_id=user_id
                )
                record = await result.single()
                if record:
                    node = record["n"]
                    return dict(node)
                return None
        except Exception as e:
            print(f"Neo4j create node error: {e}")
            return None
    
    async def create_relationship(
        self,
        from_node_id: str,
        to_node_id: str,
        relation_type: str,
        properties: Dict[str, Any] = None
    ) -> bool:
        """Create a relationship between two nodes"""
        if not self.driver:
            return False
        
        query = f"""
        MATCH (a:KnowledgeNode {{node_id: $from_id}})
        MATCH (b:KnowledgeNode {{node_id: $to_id}})
        MERGE (a)-[r:{relation_type}]->(b)
        SET r.created_at = datetime()
        RETURN r
        """
        
        try:
            async with self.driver.session(database=NEO4J_DATABASE) as session:
                result = await session.run(
                    query,
                    from_id=from_node_id,
                    to_id=to_node_id
                )
                record = await result.single()
                return record is not None
        except Exception as e:
            print(f"Neo4j create relationship error: {e}")
            return False
    
    async def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific node by ID"""
        if not self.driver:
            return None
        
        query = """
        MATCH (n:KnowledgeNode {node_id: $node_id})
        OPTIONAL MATCH (n)-[r]-(connected:KnowledgeNode)
        RETURN n, collect(DISTINCT {
            node_id: connected.node_id,
            type: connected.type,
            title: connected.title,
            relation: type(r)
        }) as connections
        """
        
        try:
            async with self.driver.session(database=NEO4J_DATABASE) as session:
                result = await session.run(query, node_id=node_id)
                record = await result.single()
                if record:
                    node = dict(record["n"])
                    node["connections"] = [c for c in record["connections"] if c["node_id"]]
                    return node
                return None
        except Exception as e:
            print(f"Neo4j get node error: {e}")
            return None
    
    async def get_nodes_by_user(
        self, 
        user_id: str, 
        node_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get all nodes for a user"""
        if not self.driver:
            return []
        
        if node_type:
            query = """
            MATCH (n:KnowledgeNode {user_id: $user_id, type: $node_type})
            RETURN n
            ORDER BY n.created_at DESC
            LIMIT $limit
            """
            params = {"user_id": user_id, "node_type": node_type, "limit": limit}
        else:
            query = """
            MATCH (n:KnowledgeNode {user_id: $user_id})
            RETURN n
            ORDER BY n.created_at DESC
            LIMIT $limit
            """
            params = {"user_id": user_id, "limit": limit}
        
        try:
            async with self.driver.session(database=NEO4J_DATABASE) as session:
                result = await session.run(query, **params)
                nodes = []
                async for record in result:
                    nodes.append(dict(record["n"]))
                return nodes
        except Exception as e:
            print(f"Neo4j get nodes error: {e}")
            return []
    
    async def get_graph_data(self, user_id: str) -> Dict[str, Any]:
        """Get full graph data for visualization"""
        if not self.driver:
            return {"nodes": [], "edges": []}
        
        query = """
        MATCH (n:KnowledgeNode {user_id: $user_id})
        OPTIONAL MATCH (n)-[r]-(m:KnowledgeNode {user_id: $user_id})
        RETURN n, collect(DISTINCT {
            source: n.node_id,
            target: m.node_id,
            type: type(r)
        }) as relationships
        """
        
        try:
            async with self.driver.session(database=NEO4J_DATABASE) as session:
                result = await session.run(query, user_id=user_id)
                
                nodes = []
                edges = []
                seen_edges = set()
                
                async for record in result:
                    node = dict(record["n"])
                    nodes.append(node)
                    
                    for rel in record["relationships"]:
                        if rel["target"]:
                            edge_key = tuple(sorted([rel["source"], rel["target"]]))
                            if edge_key not in seen_edges:
                                edges.append({
                                    "source": rel["source"],
                                    "target": rel["target"],
                                    "type": rel["type"]
                                })
                                seen_edges.add(edge_key)
                
                return {"nodes": nodes, "edges": edges}
        except Exception as e:
            print(f"Neo4j get graph error: {e}")
            return {"nodes": [], "edges": []}
    
    async def search_nodes(
        self, 
        user_id: str, 
        query: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Full-text search on nodes (basic implementation)"""
        if not self.driver:
            return []
        
        search_query = """
        MATCH (n:KnowledgeNode {user_id: $user_id})
        WHERE toLower(n.title) CONTAINS toLower($query)
           OR toLower(n.content) CONTAINS toLower($query)
        RETURN n
        ORDER BY n.created_at DESC
        LIMIT $limit
        """
        
        try:
            async with self.driver.session(database=NEO4J_DATABASE) as session:
                result = await session.run(
                    search_query,
                    user_id=user_id,
                    query=query,
                    limit=limit
                )
                nodes = []
                async for record in result:
                    nodes.append(dict(record["n"]))
                return nodes
        except Exception as e:
            print(f"Neo4j search error: {e}")
            return []
    
    async def delete_node(self, node_id: str, user_id: str) -> bool:
        """Delete a node and its relationships"""
        if not self.driver:
            return False
        
        query = """
        MATCH (n:KnowledgeNode {node_id: $node_id, user_id: $user_id})
        DETACH DELETE n
        RETURN count(n) as deleted
        """
        
        try:
            async with self.driver.session(database=NEO4J_DATABASE) as session:
                result = await session.run(query, node_id=node_id, user_id=user_id)
                record = await result.single()
                return record and record["deleted"] > 0
        except Exception as e:
            print(f"Neo4j delete error: {e}")
            return False
    
    async def get_node_stats(self, user_id: str) -> Dict[str, Any]:
        """Get statistics about user's knowledge graph"""
        if not self.driver:
            return {}
        
        query = """
        MATCH (n:KnowledgeNode {user_id: $user_id})
        WITH n.type as type, count(*) as count
        RETURN collect({type: type, count: count}) as distribution,
               sum(count) as total
        """
        
        try:
            async with self.driver.session(database=NEO4J_DATABASE) as session:
                result = await session.run(query, user_id=user_id)
                record = await result.single()
                if record:
                    dist = {item["type"]: item["count"] for item in record["distribution"]}
                    return {
                        "total_nodes": record["total"],
                        "distribution": dist
                    }
                return {"total_nodes": 0, "distribution": {}}
        except Exception as e:
            print(f"Neo4j stats error: {e}")
            return {"total_nodes": 0, "distribution": {}}
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test Neo4j connection"""
        if not self.is_configured:
            return {"connected": False, "error": "Neo4j not configured"}
        
        try:
            if not self.driver:
                await self.connect()
            
            if self.driver:
                async with self.driver.session(database=NEO4J_DATABASE) as session:
                    result = await session.run("RETURN 1 as test")
                    await result.single()
                    return {
                        "connected": True,
                        "database": NEO4J_DATABASE,
                        "uri": self.active_uri or NEO4J_URI,
                    }
            return {"connected": False, "error": "Driver not initialized"}
        except Exception as e:
            return {"connected": False, "error": str(e)}


# Singleton instance
neo4j_service = Neo4jService()
