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
    BASE_URL = "https://27c4ad23-b20f-41cf-b584-cd36c03b1a52.preview.emergentagent.com"
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
    
    # Print summary
    tester.print_summary()
    
    # Return exit code
    return 0 if len(tester.failed_tests) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
