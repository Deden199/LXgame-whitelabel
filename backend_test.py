#!/usr/bin/env python3

import requests
import sys
from datetime import datetime

class GamesPlatformTester:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.session = requests.Session()
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        if headers:
            test_headers.update(headers)
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = self.session.get(url, headers=test_headers)
            elif method == 'POST':
                response = self.session.post(url, json=data, headers=test_headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                return True, response.json() if response.content else {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                if response.content:
                    print(f"Response: {response.text[:200]}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_tenant_info(self):
        """Test tenant information"""
        return self.run_test(
            "Tenant Info (aurumbet)",
            "GET", 
            "api/tenants/slug/aurumbet",
            200
        )

    def test_player_login(self):
        """Test player login"""
        login_data = {
            "email": "player1@aurumbet.demo", 
            "password": "player123",
            "tenant_slug": "aurumbet"
        }
        
        success, response = self.run_test(
            "Player Demo Login",
            "POST",
            "api/auth/login",
            200,
            data=login_data
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            # Set authorization header for subsequent requests
            self.session.headers.update({'Authorization': f'Bearer {self.token}'})
            print(f"✅ Login token obtained")
            return True
        return False

    def test_games_api(self):
        """Test games API"""
        return self.run_test(
            "Games List",
            "GET",
            "api/games",
            200
        )

    def test_providers_api(self):
        """Test providers API"""  
        return self.run_test(
            "Providers List",
            "GET",
            "api/providers",
            200
        )

    def test_categories_api(self):
        """Test game categories API"""
        return self.run_test(
            "Game Categories",
            "GET", 
            "api/games/categories",
            200
        )

    def test_games_search(self):
        """Test games search"""
        return self.run_test(
            "Games Search",
            "GET",
            "api/games?search=slot",
            200
        )

    def test_games_filter_hot(self):
        """Test hot games filter"""
        return self.run_test(
            "Hot Games Filter", 
            "GET",
            "api/games?tag=hot",
            200
        )

def main():
    print("🎮 Starting Games Platform Backend Testing...")
    print("=" * 50)
    
    tester = GamesPlatformTester()
    
    # Test sequence
    tests = [
        ("Tenant Info", tester.test_tenant_info),
        ("Player Login", tester.test_player_login),
        ("Games API", tester.test_games_api),
        ("Providers API", tester.test_providers_api),  
        ("Categories API", tester.test_categories_api),
        ("Games Search", tester.test_games_search),
        ("Hot Games Filter", tester.test_games_filter_hot)
    ]
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            if not success and test_name == "Player Login":
                print("❌ Login failed, stopping dependent tests")
                break
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {str(e)}")
    
    # Print results
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} passed")
    
    if tester.tests_passed == tester.tests_run:
        print("✅ All tests passed - Backend APIs working correctly")
        return 0
    else:
        print("❌ Some tests failed - Check backend configuration")
        return 1

if __name__ == "__main__":
    sys.exit(main())