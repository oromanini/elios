import requests
import sys
import json
from datetime import datetime

class ELIOSAPITester:
    def __init__(self, base_url="https://elios-coach.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.admin_user_id = None
        self.test_user_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    if isinstance(response_data, dict) and len(str(response_data)) < 500:
                        print(f"   Response: {response_data}")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test root API endpoint"""
        return self.run_test("Root API", "GET", "", 200)

    def test_admin_login(self):
        """Test admin login"""
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "auth/login",
            200,
            data={"email": "admin@hutooeducacao.com", "password": "Admin@123"}
        )
        if success and 'token' in response:
            self.token = response['token']
            self.admin_user_id = response.get('user', {}).get('id')
            print(f"   Admin logged in successfully, user_id: {self.admin_user_id}")
            return True
        return False

    def test_get_current_user(self):
        """Test getting current user info"""
        return self.run_test("Get Current User", "GET", "auth/me", 200)

    def test_init_questions(self):
        """Test initializing default questions"""
        return self.run_test("Initialize Questions", "POST", "init/questions", 200)

    def test_get_questions(self):
        """Test getting all questions"""
        return self.run_test("Get Questions", "GET", "questions", 200)

    def test_admin_get_questions(self):
        """Test admin getting all questions"""
        return self.run_test("Admin Get Questions", "GET", "admin/questions", 200)

    def test_form_submission(self):
        """Test form submission (creates new user)"""
        timestamp = datetime.now().strftime("%H%M%S")
        test_email = f"test_user_{timestamp}@test.com"
        
        # First get questions to create responses
        success, questions_data = self.run_test("Get Questions for Form", "GET", "questions", 200)
        if not success or not questions_data:
            print("❌ Cannot test form submission - no questions available")
            return False
        
        # Create responses for all questions
        responses = []
        for i, question in enumerate(questions_data[:3]):  # Test with first 3 questions only
            responses.append({
                "question_id": question["id"],
                "answer": f"Test answer for {question['pillar']} - This is a detailed response for testing purposes."
            })
        
        form_data = {
            "full_name": f"Test User {timestamp}",
            "email": test_email,
            "responses": responses
        }
        
        success, response = self.run_test(
            "Form Submission",
            "POST",
            "form/submit",
            200,
            data=form_data
        )
        
        if success:
            self.test_user_id = response.get('user_id')
            print(f"   Test user created with ID: {self.test_user_id}")
        
        return success

    def test_admin_list_users(self):
        """Test admin listing users"""
        return self.run_test("Admin List Users", "GET", "admin/users", 200)

    def test_dashboard_stats(self):
        """Test dashboard statistics"""
        return self.run_test("Dashboard Stats", "GET", "dashboard/stats", 200)

    def test_goals_operations(self):
        """Test goals CRUD operations"""
        # List goals
        success1, _ = self.run_test("List Goals", "GET", "goals", 200)
        
        # Create a goal
        goal_data = {
            "pillar": "ESPIRITUALIDADE",
            "title": "Test Goal",
            "description": "This is a test goal for API testing",
            "target_date": "2025-12-31"
        }
        success2, goal_response = self.run_test("Create Goal", "POST", "goals", 200, data=goal_data)
        
        goal_id = None
        if success2 and goal_response:
            goal_id = goal_response.get('id')
        
        # Update goal if created
        success3 = True
        if goal_id:
            update_data = {"title": "Updated Test Goal"}
            success3, _ = self.run_test(f"Update Goal {goal_id}", "PUT", f"goals/{goal_id}", 200, data=update_data)
        
        # Delete goal if created
        success4 = True
        if goal_id:
            success4, _ = self.run_test(f"Delete Goal {goal_id}", "DELETE", f"goals/{goal_id}", 200)
        
        return success1 and success2 and success3 and success4

    def test_ai_analyze(self):
        """Test AI analysis endpoint"""
        analyze_data = {
            "pillar": "ESPIRITUALIDADE",
            "question": "Como estou e como desejo claramente estar em 12 meses?",
            "answer": "Atualmente pratico meditação 2x por semana, quero chegar a praticar diariamente e ter mais conexão espiritual."
        }
        return self.run_test("AI Analyze Response", "POST", "ai/analyze", 200, data=analyze_data)

    def test_ai_chat(self):
        """Test AI chat endpoint"""
        chat_data = {
            "message": "Olá ELIOS, como você pode me ajudar com meus objetivos?",
            "context": "Teste de integração"
        }
        return self.run_test("AI Chat", "POST", "ai/chat", 200, data=chat_data)

    def test_chat_history(self):
        """Test chat history endpoints"""
        success1, _ = self.run_test("Get Chat History", "GET", "ai/chat/history", 200)
        return success1

    def test_form_responses(self):
        """Test getting form responses"""
        return self.run_test("Get Form Responses", "GET", "form/responses", 200)

    def test_admin_ai_knowledge(self):
        """Test AI knowledge management"""
        # List knowledge
        success1, _ = self.run_test("List AI Knowledge", "GET", "admin/ai/knowledge", 200)
        
        # Add knowledge
        knowledge_data = {
            "category": "TEST",
            "content": "This is test knowledge for API testing",
            "priority": 1
        }
        success2, knowledge_response = self.run_test("Add AI Knowledge", "POST", "admin/ai/knowledge", 200, data=knowledge_data)
        
        # Delete knowledge if created
        success3 = True
        if success2 and knowledge_response:
            knowledge_id = knowledge_response.get('id')
            if knowledge_id:
                success3, _ = self.run_test(f"Delete AI Knowledge {knowledge_id}", "DELETE", f"admin/ai/knowledge/{knowledge_id}", 200)
        
        return success1 and success2 and success3

def main():
    print("🚀 Starting ELIOS API Testing...")
    print("=" * 60)
    
    tester = ELIOSAPITester()
    
    # Test sequence
    tests = [
        ("Root Endpoint", tester.test_root_endpoint),
        ("Admin Login", tester.test_admin_login),
        ("Get Current User", tester.test_get_current_user),
        ("Initialize Questions", tester.test_init_questions),
        ("Get Questions", tester.test_get_questions),
        ("Admin Get Questions", tester.test_admin_get_questions),
        ("Form Submission", tester.test_form_submission),
        ("Admin List Users", tester.test_admin_list_users),
        ("Dashboard Stats", tester.test_dashboard_stats),
        ("Goals Operations", tester.test_goals_operations),
        ("AI Analyze", tester.test_ai_analyze),
        ("AI Chat", tester.test_ai_chat),
        ("Chat History", tester.test_chat_history),
        ("Form Responses", tester.test_form_responses),
        ("Admin AI Knowledge", tester.test_admin_ai_knowledge),
    ]
    
    failed_tests = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            success = test_func()
            if not success:
                failed_tests.append(test_name)
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            failed_tests.append(test_name)
    
    # Print final results
    print(f"\n{'='*60}")
    print(f"📊 FINAL RESULTS")
    print(f"{'='*60}")
    print(f"Tests passed: {tester.tests_passed}/{tester.tests_run}")
    print(f"Success rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    if failed_tests:
        print(f"\n❌ Failed tests:")
        for test in failed_tests:
            print(f"   - {test}")
    else:
        print(f"\n✅ All tests passed!")
    
    return 0 if len(failed_tests) == 0 else 1

if __name__ == "__main__":
    sys.exit(main())