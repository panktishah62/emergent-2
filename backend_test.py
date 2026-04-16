import requests
import sys
import json
from datetime import datetime

class PriceHunterAPITester:
    def __init__(self, base_url="https://deal-finder-593.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
        
        self.test_results.append({
            "test": name,
            "status": "PASSED" if success else "FAILED",
            "details": details
        })

    def test_api_health(self):
        """Test basic API health"""
        try:
            response = requests.get(f"{self.api_url}/", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}, Response: {response.text[:100]}"
            self.log_test("API Health Check", success, details)
            return success
        except Exception as e:
            self.log_test("API Health Check", False, str(e))
            return False

    def test_search_basic(self):
        """Test basic search functionality"""
        try:
            payload = {
                "query": "iPhone 15",
                "location": "Mumbai"
            }
            response = requests.post(f"{self.api_url}/search", json=payload, timeout=30)
            
            if response.status_code != 200:
                self.log_test("Basic Search", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
            
            data = response.json()
            
            # Validate response structure
            required_fields = ['results', 'total_results', 'online_count', 'offline_count', 'search_time', 'parsed_intent']
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                self.log_test("Basic Search", False, f"Missing fields: {missing_fields}")
                return False
            
            # Validate results structure
            if not data['results']:
                self.log_test("Basic Search", False, "No results returned")
                return False
            
            result = data['results'][0]
            result_fields = ['id', 'rank', 'source_type', 'vendor_name', 'price', 'delivery_time', 'confidence', 'is_best_deal']
            missing_result_fields = [field for field in result_fields if field not in result]
            
            if missing_result_fields:
                self.log_test("Basic Search", False, f"Missing result fields: {missing_result_fields}")
                return False
            
            self.log_test("Basic Search", True, f"Found {data['total_results']} results in {data['search_time']}s")
            return True
            
        except Exception as e:
            self.log_test("Basic Search", False, str(e))
            return False

    def test_search_without_location(self):
        """Test search without location parameter"""
        try:
            payload = {
                "query": "best price for tomatoes"
            }
            response = requests.post(f"{self.api_url}/search", json=payload, timeout=30)
            
            success = response.status_code == 200
            if success:
                data = response.json()
                details = f"Found {data['total_results']} results"
            else:
                details = f"Status: {response.status_code}"
            
            self.log_test("Search Without Location", success, details)
            return success
            
        except Exception as e:
            self.log_test("Search Without Location", False, str(e))
            return False

    def test_search_complex_query(self):
        """Test complex natural language query"""
        try:
            payload = {
                "query": "cheapest iPhone 15 near Koramangala",
                "location": "Bangalore"
            }
            response = requests.post(f"{self.api_url}/search", json=payload, timeout=30)
            
            if response.status_code != 200:
                self.log_test("Complex Query Search", False, f"Status: {response.status_code}")
                return False
            
            data = response.json()
            
            # Check if OpenAI parsing worked
            parsed_intent = data.get('parsed_intent', {})
            if not parsed_intent:
                self.log_test("Complex Query Search", False, "No parsed intent returned")
                return False
            
            # Validate that results are ranked (first should be best deal)
            if data['results'] and data['results'][0]['is_best_deal']:
                self.log_test("Complex Query Search", True, f"Parsed intent: {parsed_intent}")
                return True
            else:
                self.log_test("Complex Query Search", False, "Best deal not properly ranked")
                return False
            
        except Exception as e:
            self.log_test("Complex Query Search", False, str(e))
            return False

    def test_online_offline_results(self):
        """Test that both online and offline results are generated"""
        try:
            payload = {
                "query": "laptop",
                "location": "Delhi"
            }
            response = requests.post(f"{self.api_url}/search", json=payload, timeout=30)
            
            if response.status_code != 200:
                self.log_test("Online/Offline Results", False, f"Status: {response.status_code}")
                return False
            
            data = response.json()
            
            online_count = data.get('online_count', 0)
            offline_count = data.get('offline_count', 0)
            
            if online_count > 0 and offline_count > 0:
                # Check if results actually contain both types
                online_results = [r for r in data['results'] if r['source_type'] == 'ONLINE']
                offline_results = [r for r in data['results'] if r['source_type'] == 'OFFLINE']
                
                if len(online_results) > 0 and len(offline_results) > 0:
                    self.log_test("Online/Offline Results", True, f"Online: {online_count}, Offline: {offline_count}")
                    return True
                else:
                    self.log_test("Online/Offline Results", False, "Results don't match counts")
                    return False
            else:
                self.log_test("Online/Offline Results", False, f"Missing result types - Online: {online_count}, Offline: {offline_count}")
                return False
            
        except Exception as e:
            self.log_test("Online/Offline Results", False, str(e))
            return False

    def test_price_formatting(self):
        """Test that prices are properly formatted"""
        try:
            payload = {
                "query": "smartphone",
                "location": "Chennai"
            }
            response = requests.post(f"{self.api_url}/search", json=payload, timeout=30)
            
            if response.status_code != 200:
                self.log_test("Price Formatting", False, f"Status: {response.status_code}")
                return False
            
            data = response.json()
            
            for result in data['results']:
                price = result.get('price')
                if not isinstance(price, (int, float)) or price <= 0:
                    self.log_test("Price Formatting", False, f"Invalid price: {price}")
                    return False
            
            self.log_test("Price Formatting", True, "All prices are valid numbers")
            return True
            
        except Exception as e:
            self.log_test("Price Formatting", False, str(e))
            return False

    def test_confidence_scores(self):
        """Test that confidence scores are within valid range"""
        try:
            payload = {
                "query": "headphones",
                "location": "Pune"
            }
            response = requests.post(f"{self.api_url}/search", json=payload, timeout=30)
            
            if response.status_code != 200:
                self.log_test("Confidence Scores", False, f"Status: {response.status_code}")
                return False
            
            data = response.json()
            
            for result in data['results']:
                confidence = result.get('confidence')
                if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
                    self.log_test("Confidence Scores", False, f"Invalid confidence: {confidence}")
                    return False
            
            self.log_test("Confidence Scores", True, "All confidence scores are valid (0-1)")
            return True
            
        except Exception as e:
            self.log_test("Confidence Scores", False, str(e))
            return False

    def test_empty_query(self):
        """Test handling of empty query"""
        try:
            payload = {
                "query": "",
                "location": "Mumbai"
            }
            response = requests.post(f"{self.api_url}/search", json=payload, timeout=30)
            
            # Should either handle gracefully or return appropriate error
            if response.status_code in [200, 400, 422]:
                self.log_test("Empty Query Handling", True, f"Status: {response.status_code}")
                return True
            else:
                self.log_test("Empty Query Handling", False, f"Unexpected status: {response.status_code}")
                return False
            
        except Exception as e:
            self.log_test("Empty Query Handling", False, str(e))
            return False

    def run_all_tests(self):
        """Run all tests and return summary"""
        print("🚀 Starting PriceHunter API Tests...")
        print(f"Testing against: {self.base_url}")
        print("=" * 50)
        
        # Run tests in order
        tests = [
            self.test_api_health,
            self.test_search_basic,
            self.test_search_without_location,
            self.test_search_complex_query,
            self.test_online_offline_results,
            self.test_price_formatting,
            self.test_confidence_scores,
            self.test_empty_query
        ]
        
        for test in tests:
            test()
            print()
        
        # Print summary
        print("=" * 50)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return True
        else:
            print("⚠️  Some tests failed. Check details above.")
            return False

def main():
    tester = PriceHunterAPITester()
    success = tester.run_all_tests()
    
    # Save detailed results
    with open('/app/test_reports/backend_test_results.json', 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_tests': tester.tests_run,
            'passed_tests': tester.tests_passed,
            'success_rate': f"{(tester.tests_passed/tester.tests_run)*100:.1f}%",
            'results': tester.test_results
        }, f, indent=2)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())