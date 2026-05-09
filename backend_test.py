"""
CorteQS Intelligence Engine - Backend API Testing
Tests all API endpoints with authentication
"""

import requests
import sys
from datetime import datetime

class CorteQSAPITester:
    def __init__(self, base_url, session_token):
        self.base_url = base_url
        self.session_token = session_token
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {session_token}'
        }
        
    def run_test(self, name, method, endpoint, expected_status, data=None, check_response=None):
        """Run a single API test"""
        url = f"{self.base_url}{endpoint}"
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=self.headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=self.headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=self.headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=self.headers, timeout=10)
            
            print(f"   Status: {response.status_code}")
            
            success = response.status_code == expected_status
            
            if success:
                # Additional response validation if provided
                if check_response and response.status_code == expected_status:
                    try:
                        response_data = response.json()
                        if not check_response(response_data):
                            success = False
                            print(f"❌ Failed - Response validation failed")
                            self.failed_tests.append({
                                'name': name,
                                'endpoint': endpoint,
                                'reason': 'Response validation failed',
                                'status': response.status_code
                            })
                        else:
                            self.tests_passed += 1
                            print(f"✅ Passed")
                    except Exception as e:
                        success = False
                        print(f"❌ Failed - Response validation error: {str(e)}")
                        self.failed_tests.append({
                            'name': name,
                            'endpoint': endpoint,
                            'reason': f'Response validation error: {str(e)}',
                            'status': response.status_code
                        })
                else:
                    self.tests_passed += 1
                    print(f"✅ Passed")
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Response: {response.text[:200]}")
                self.failed_tests.append({
                    'name': name,
                    'endpoint': endpoint,
                    'reason': f'Expected {expected_status}, got {response.status_code}',
                    'status': response.status_code
                })
            
            return success, response.json() if success and response.text else {}
            
        except requests.exceptions.Timeout:
            print(f"❌ Failed - Request timeout")
            self.failed_tests.append({
                'name': name,
                'endpoint': endpoint,
                'reason': 'Request timeout',
                'status': 'timeout'
            })
            return False, {}
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed - Request error: {str(e)}")
            self.failed_tests.append({
                'name': name,
                'endpoint': endpoint,
                'reason': f'Request error: {str(e)}',
                'status': 'error'
            })
            return False, {}
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.failed_tests.append({
                'name': name,
                'endpoint': endpoint,
                'reason': f'Error: {str(e)}',
                'status': 'error'
            })
            return False, {}

    def test_health(self):
        """Test health check endpoint"""
        success, response = self.run_test(
            "Health Check",
            "GET",
            "/api/health",
            200,
            check_response=lambda r: r.get('status') == 'healthy'
        )
        return success

    def test_auth_me(self):
        """Test get current user endpoint"""
        success, response = self.run_test(
            "Get Current User",
            "GET",
            "/api/auth/me",
            200,
            check_response=lambda r: 'user_id' in r and 'email' in r
        )
        return success, response

    def test_get_data_sources(self):
        """Test get data sources endpoint"""
        success, response = self.run_test(
            "Get Data Sources",
            "GET",
            "/api/data-sources",
            200,
            check_response=lambda r: isinstance(r, list)
        )
        return success, response

    def test_create_data_source(self):
        """Test create data source endpoint"""
        data = {
            "source_type": "slack",
            "name": f"Test Slack {datetime.now().strftime('%H%M%S')}",
            "config": {}
        }
        success, response = self.run_test(
            "Create Data Source",
            "POST",
            "/api/data-sources",
            200,
            data=data,
            check_response=lambda r: 'source_id' in r and r.get('name') == data['name']
        )
        return success, response

    def test_connect_data_source(self, source_id):
        """Test connect data source endpoint"""
        success, response = self.run_test(
            "Connect Data Source",
            "PUT",
            f"/api/data-sources/{source_id}/connect",
            200,
            check_response=lambda r: r.get('status') == 'connected'
        )
        return success

    def test_disconnect_data_source(self, source_id):
        """Test disconnect data source endpoint"""
        success, response = self.run_test(
            "Disconnect Data Source",
            "PUT",
            f"/api/data-sources/{source_id}/disconnect",
            200,
            check_response=lambda r: r.get('status') == 'disconnected'
        )
        return success

    def test_delete_data_source(self, source_id):
        """Test delete data source endpoint"""
        success, response = self.run_test(
            "Delete Data Source",
            "DELETE",
            f"/api/data-sources/{source_id}",
            200
        )
        return success

    def test_get_knowledge_nodes(self):
        """Test get knowledge nodes endpoint"""
        success, response = self.run_test(
            "Get Knowledge Nodes",
            "GET",
            "/api/knowledge/nodes",
            200,
            check_response=lambda r: isinstance(r, list)
        )
        return success, response

    def test_create_knowledge_node(self):
        """Test create knowledge node endpoint"""
        data = {
            "node_type": "topic",
            "title": f"Test Topic {datetime.now().strftime('%H%M%S')}",
            "content": "This is a test knowledge node",
            "metadata": {}
        }
        success, response = self.run_test(
            "Create Knowledge Node",
            "POST",
            "/api/knowledge/nodes",
            200,
            data=data,
            check_response=lambda r: 'node_id' in r and r.get('title') == data['title']
        )
        return success, response

    def test_get_knowledge_node(self, node_id):
        """Test get specific knowledge node endpoint"""
        success, response = self.run_test(
            "Get Knowledge Node",
            "GET",
            f"/api/knowledge/nodes/{node_id}",
            200,
            check_response=lambda r: r.get('node_id') == node_id
        )
        return success

    def test_get_knowledge_graph(self):
        """Test get knowledge graph endpoint"""
        success, response = self.run_test(
            "Get Knowledge Graph",
            "GET",
            "/api/knowledge/graph",
            200,
            check_response=lambda r: 'nodes' in r and 'edges' in r
        )
        return success

    def test_chat(self):
        """Test AI chat endpoint"""
        data = {
            "message": "What data sources are connected?"
        }
        success, response = self.run_test(
            "AI Chat",
            "POST",
            "/api/chat",
            200,
            data=data,
            check_response=lambda r: 'user_message' in r and 'assistant_message' in r
        )
        return success

    def test_get_chat_history(self):
        """Test get chat history endpoint"""
        success, response = self.run_test(
            "Get Chat History",
            "GET",
            "/api/chat/history",
            200,
            check_response=lambda r: isinstance(r, list)
        )
        return success

    def test_search_knowledge(self):
        """Test search knowledge endpoint"""
        data = {
            "query": "test",
            "filters": {},
            "limit": 20
        }
        success, response = self.run_test(
            "Search Knowledge",
            "POST",
            "/api/search",
            200,
            data=data,
            check_response=lambda r: 'results' in r and 'count' in r
        )
        return success

    def test_get_analytics_overview(self):
        """Test get analytics overview endpoint"""
        success, response = self.run_test(
            "Get Analytics Overview",
            "GET",
            "/api/analytics/overview",
            200,
            check_response=lambda r: 'statistics' in r
        )
        return success

    def test_get_activities(self):
        """Test get activities endpoint"""
        success, response = self.run_test(
            "Get Activities",
            "GET",
            "/api/activities",
            200,
            check_response=lambda r: isinstance(r, list)
        )
        return success

    # ==================== V2.0 INTEGRATION TESTS ====================
    
    def test_integration_status(self):
        """Test integration status endpoint"""
        success, response = self.run_test(
            "Get Integration Status",
            "GET",
            "/api/integrations/status",
            200,
            check_response=lambda r: 'slack' in r and 'github' in r and 'neo4j' in r
        )
        return success, response
    
    def test_slack_connection(self):
        """Test Slack connection endpoint"""
        success, response = self.run_test(
            "Test Slack Connection",
            "GET",
            "/api/integrations/slack/test",
            200,
            check_response=lambda r: 'connected' in r
        )
        return success, response
    
    def test_github_connection(self):
        """Test GitHub connection endpoint"""
        success, response = self.run_test(
            "Test GitHub Connection",
            "GET",
            "/api/integrations/github/test",
            200,
            check_response=lambda r: 'connected' in r
        )
        return success, response
    
    def test_neo4j_status(self):
        """Test Neo4j status endpoint"""
        success, response = self.run_test(
            "Test Neo4j Status",
            "GET",
            "/api/neo4j/status",
            200,
            check_response=lambda r: 'connected' in r
        )
        return success, response
    
    def test_elasticsearch_status(self):
        """Test Elasticsearch status endpoint"""
        success, response = self.run_test(
            "Test Elasticsearch Status",
            "GET",
            "/api/elasticsearch/status",
            200,
            check_response=lambda r: 'connected' in r
        )
        return success, response
    
    def test_neo4j_stats(self):
        """Test Neo4j graph statistics endpoint"""
        success, response = self.run_test(
            "Get Neo4j Graph Stats",
            "GET",
            "/api/neo4j/stats",
            200,
            check_response=lambda r: 'total_nodes' in r or 'error' not in r
        )
        return success, response
    
    def test_neo4j_graph(self):
        """Test Neo4j graph data endpoint"""
        success, response = self.run_test(
            "Get Neo4j Graph Data",
            "GET",
            "/api/neo4j/graph",
            200,
            check_response=lambda r: 'nodes' in r and 'edges' in r
        )
        return success, response
    
    def test_elasticsearch_search_stats(self):
        """Test Elasticsearch search statistics endpoint"""
        success, response = self.run_test(
            "Get Elasticsearch Search Stats",
            "GET",
            "/api/search/stats",
            200,
            check_response=lambda r: 'total_documents' in r or 'error' not in r
        )
        return success, response
    
    def test_slack_sync(self):
        """Test Slack data sync endpoint"""
        success, response = self.run_test(
            "Sync Slack Data",
            "POST",
            "/api/integrations/slack/sync",
            200,
            check_response=lambda r: 'success' in r
        )
        return success, response
    
    def test_github_sync(self):
        """Test GitHub data sync endpoint"""
        # GitHub sync can take longer due to many repos
        url = f"{self.base_url}/api/integrations/github/sync"
        self.tests_run += 1
        print(f"\n🔍 Testing Sync GitHub Data...")
        print(f"   URL: {url}")
        print(f"   Note: This may take longer due to multiple repositories...")
        
        try:
            response = requests.post(
                url, 
                headers=self.headers,
                timeout=90  # Increased timeout for GitHub sync
            )
            
            print(f"   Status: {response.status_code}")
            
            success = response.status_code == 200
            
            if success:
                response_data = response.json()
                if 'success' in response_data:
                    self.tests_passed += 1
                    print(f"✅ Passed")
                    return True, response_data
                else:
                    print(f"❌ Failed - Invalid response structure")
                    self.failed_tests.append({
                        'name': 'Sync GitHub Data',
                        'endpoint': '/api/integrations/github/sync',
                        'reason': 'Invalid response structure',
                        'status': response.status_code
                    })
                    return False, {}
            else:
                print(f"❌ Failed - Expected 200, got {response.status_code}")
                self.failed_tests.append({
                    'name': 'Sync GitHub Data',
                    'endpoint': '/api/integrations/github/sync',
                    'reason': f'Expected 200, got {response.status_code}',
                    'status': response.status_code
                })
                return False, {}
                
        except requests.exceptions.Timeout:
            print(f"❌ Failed - Request timeout (>90s)")
            self.failed_tests.append({
                'name': 'Sync GitHub Data',
                'endpoint': '/api/integrations/github/sync',
                'reason': 'Request timeout (>90s) - too many repositories',
                'status': 'timeout'
            })
            return False, {}
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.failed_tests.append({
                'name': 'Sync GitHub Data',
                'endpoint': '/api/integrations/github/sync',
                'reason': f'Error: {str(e)}',
                'status': 'error'
            })
            return False, {}
    
    def test_document_upload(self):
        """Test document upload endpoint"""
        import io
        # Create a simple text file
        file_content = "This is a test document for CorteQS Intelligence Engine.\nIt contains sample text for AI extraction."
        
        # Use requests with files parameter
        url = f"{self.base_url}/api/documents/upload"
        files = {'file': ('test_document.txt', io.BytesIO(file_content.encode()), 'text/plain')}
        
        self.tests_run += 1
        print(f"\n🔍 Testing Document Upload...")
        print(f"   URL: {url}")
        
        try:
            response = requests.post(
                url, 
                files=files, 
                headers={'Authorization': f'Bearer {self.session_token}'},
                timeout=30  # Longer timeout for AI extraction
            )
            
            print(f"   Status: {response.status_code}")
            
            success = response.status_code == 200
            
            if success:
                response_data = response.json()
                if 'document' in response_data and 'knowledge_node_id' in response_data:
                    self.tests_passed += 1
                    print(f"✅ Passed")
                    return True, response_data
                else:
                    print(f"❌ Failed - Invalid response structure")
                    self.failed_tests.append({
                        'name': 'Document Upload',
                        'endpoint': '/api/documents/upload',
                        'reason': 'Invalid response structure',
                        'status': response.status_code
                    })
                    return False, {}
            else:
                print(f"❌ Failed - Expected 200, got {response.status_code}")
                self.failed_tests.append({
                    'name': 'Document Upload',
                    'endpoint': '/api/documents/upload',
                    'reason': f'Expected 200, got {response.status_code}',
                    'status': response.status_code
                })
                return False, {}
                
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.failed_tests.append({
                'name': 'Document Upload',
                'endpoint': '/api/documents/upload',
                'reason': f'Error: {str(e)}',
                'status': 'error'
            })
            return False, {}
    
    def test_get_documents(self):
        """Test get documents endpoint"""
        success, response = self.run_test(
            "Get Documents",
            "GET",
            "/api/documents",
            200,
            check_response=lambda r: 'documents' in r and isinstance(r['documents'], list)
        )
        return success, response
    
    def test_full_text_search(self):
        """Test full-text search endpoint"""
        data = {
            "query": "test",
            "filters": {},
            "limit": 20
        }
        # Note: Full-text search uses Elasticsearch if configured, otherwise falls back to MongoDB
        success, response = self.run_test(
            "Full-Text Search",
            "POST",
            "/api/search/full",
            200,
            data=data,
            check_response=lambda r: 'results' in r
        )
        return success, response

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {len(self.failed_tests)}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in self.failed_tests:
                print(f"  - {test['name']}")
                print(f"    Endpoint: {test['endpoint']}")
                print(f"    Reason: {test['reason']}")
                print(f"    Status: {test['status']}")
        
        print("="*60)


def main():
    # Configuration
    BASE_URL = "https://file-inspector-80.preview.emergentagent.com"
    SESSION_TOKEN = "test_session_corteqs"
    
    print("="*60)
    print("CorteQS Intelligence Engine - Backend API Testing")
    print("="*60)
    print(f"Base URL: {BASE_URL}")
    print(f"Session Token: {SESSION_TOKEN[:20]}...")
    print("="*60)
    
    tester = CorteQSAPITester(BASE_URL, SESSION_TOKEN)
    
    # Test 1: Health Check
    if not tester.test_health():
        print("\n⚠️  Health check failed - backend may not be running")
        tester.print_summary()
        return 1
    
    # Test 2: Authentication
    auth_success, user_data = tester.test_auth_me()
    if not auth_success:
        print("\n⚠️  Authentication failed - cannot proceed with authenticated tests")
        tester.print_summary()
        return 1
    
    # Test 3: Data Sources
    tester.test_get_data_sources()
    
    # Test 4: Create, Connect, Disconnect, Delete Data Source
    create_success, source_data = tester.test_create_data_source()
    if create_success and 'source_id' in source_data:
        source_id = source_data['source_id']
        tester.test_connect_data_source(source_id)
        tester.test_disconnect_data_source(source_id)
        tester.test_delete_data_source(source_id)
    
    # Test 5: Knowledge Graph
    tester.test_get_knowledge_nodes()
    
    # Test 6: Create and Get Knowledge Node
    create_success, node_data = tester.test_create_knowledge_node()
    if create_success and 'node_id' in node_data:
        node_id = node_data['node_id']
        tester.test_get_knowledge_node(node_id)
    
    # Test 7: Get Knowledge Graph
    tester.test_get_knowledge_graph()
    
    # Test 8: AI Chat
    tester.test_chat()
    tester.test_get_chat_history()
    
    # Test 9: Search
    tester.test_search_knowledge()
    
    # Test 10: Analytics
    tester.test_get_analytics_overview()
    tester.test_get_activities()
    
    # ==================== V2.0 INTEGRATION TESTS ====================
    print("\n" + "="*60)
    print("🚀 TESTING V2.0 FEATURES - REAL INTEGRATIONS")
    print("="*60)
    
    # Test 11: Integration Status
    status_success, status_data = tester.test_integration_status()
    if status_success:
        print(f"\n📊 Integration Status:")
        print(f"   Slack: {'✅ Connected' if status_data.get('slack', {}).get('connected') else '❌ Not Connected'}")
        print(f"   GitHub: {'✅ Connected' if status_data.get('github', {}).get('connected') else '❌ Not Connected'}")
        print(f"   Neo4j: {'✅ Connected' if status_data.get('neo4j', {}).get('connected') else '❌ Not Connected'}")
        print(f"   Elasticsearch: {'✅ Connected' if status_data.get('elasticsearch', {}).get('connected') else '❌ Not Connected'}")
    
    # Test 12: Individual Integration Tests
    tester.test_slack_connection()
    tester.test_github_connection()
    tester.test_neo4j_status()
    tester.test_elasticsearch_status()
    
    # Test 12a: Neo4j Stats and Graph Data
    print("\n📊 Testing Neo4j Data...")
    neo4j_stats_success, neo4j_stats = tester.test_neo4j_stats()
    if neo4j_stats_success:
        print(f"   Neo4j Stats: {neo4j_stats}")
    
    neo4j_graph_success, neo4j_graph = tester.test_neo4j_graph()
    if neo4j_graph_success:
        print(f"   Neo4j Graph: {len(neo4j_graph.get('nodes', []))} nodes, {len(neo4j_graph.get('edges', []))} edges")
    
    # Test 12b: Elasticsearch Stats
    print("\n📊 Testing Elasticsearch Data...")
    es_stats_success, es_stats = tester.test_elasticsearch_search_stats()
    if es_stats_success:
        print(f"   Elasticsearch Stats: {es_stats}")
    
    # Test 13: Data Sync (only if integrations are connected)
    if status_success and status_data.get('slack', {}).get('connected'):
        print("\n🔄 Testing Slack Sync...")
        sync_success, sync_data = tester.test_slack_sync()
        if sync_success:
            print(f"   Sync Stats: {sync_data.get('stats', {})}")
    
    if status_success and status_data.get('github', {}).get('connected'):
        print("\n🔄 Testing GitHub Sync...")
        sync_success, sync_data = tester.test_github_sync()
        if sync_success:
            print(f"   Sync Stats: {sync_data.get('stats', {})}")
    
    # Test 14: Document Upload
    upload_success, upload_data = tester.test_document_upload()
    if upload_success:
        print(f"   Document ID: {upload_data.get('document', {}).get('document_id')}")
        print(f"   Knowledge Node ID: {upload_data.get('knowledge_node_id')}")
    
    # Test 15: Get Documents
    tester.test_get_documents()
    
    # Test 16: Full-Text Search
    tester.test_full_text_search()
    
    # Print summary
    tester.print_summary()
    
    # Return exit code
    return 0 if len(tester.failed_tests) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
