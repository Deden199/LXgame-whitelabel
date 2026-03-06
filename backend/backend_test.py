#!/usr/bin/env python3
import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class GamingPlatformTester:
    def __init__(self, base_url="https://seamless-game-source.preview.emergentagent.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.tests_run = 0
        self.tests_passed = 0
        self.auth_tokens = {}
        
        # Test credentials from review request
        self.credentials = {
            "super_admin": {"email": "admin@platform.com", "password": "admin123"},
            "tenant_admin_aurum": {"email": "admin@aurumbet.com", "password": "admin123"},
            "player_aurum": {"email": "player1@aurumbet.demo", "password": "player123", "tenant_slug": "aurumbet"},
            "player_bluewave": {"email": "player1@bluewave.demo", "password": "player123", "tenant_slug": "bluewave"}
        }

    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, 
                 data: Optional[Dict] = None, headers: Optional[Dict] = None, 
                 cookies: Optional[Dict] = None, params: Optional[Dict] = None) -> tuple[bool, Dict]:
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint.lstrip('/')}"
        
        request_headers = {'Content-Type': 'application/json'}
        if headers:
            request_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {method} {url}")
        
        try:
            response = None
            if method == 'GET':
                response = self.session.get(url, headers=request_headers, cookies=cookies, params=params)
            elif method == 'POST':
                response = self.session.post(url, json=data, headers=request_headers, cookies=cookies, params=params)
            elif method == 'PUT':
                response = self.session.put(url, json=data, headers=request_headers, cookies=cookies, params=params)
            elif method == 'DELETE':
                response = self.session.delete(url, headers=request_headers, cookies=cookies, params=params)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                if response.text:
                    print(f"   Response: {response.text[:200]}")

            try:
                response_data = response.json() if response.text else {}
            except:
                response_data = {"raw_response": response.text}

            return success, response_data

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {"error": str(e)}

    def login_user(self, user_type: str) -> bool:
        """Login a user and store cookies"""
        creds = self.credentials[user_type]
        login_data = {
            "email": creds["email"], 
            "password": creds["password"]
        }
        
        # Add tenant_slug for players
        if "tenant_slug" in creds:
            login_data["tenant_slug"] = creds["tenant_slug"]
        
        success, response = self.run_test(
            f"Login {user_type}",
            "POST",
            "auth/login",
            200,
            data=login_data
        )
        
        if success and 'access_token' in response:
            # Store session cookies for this user
            self.auth_tokens[user_type] = self.session.cookies.get_dict()
            return True
        return False

    def test_authenticated_endpoint(self, user_type: str, name: str, method: str, 
                                   endpoint: str, expected_status: int = 200, data: Optional[Dict] = None) -> tuple[bool, Dict]:
        """Test an endpoint that requires authentication"""
        cookies = self.auth_tokens.get(user_type)
        if not cookies:
            print(f"❌ No auth cookies for {user_type}")
            return False, {}
        
        return self.run_test(name, method, endpoint, expected_status, data=data, cookies=cookies)

    def test_health_endpoints(self):
        """Test basic health and info endpoints"""
        print("\n" + "="*50)
        print("TESTING HEALTH ENDPOINTS")
        print("="*50)
        
        self.run_test("API Root", "GET", "", 200)
        self.run_test("Health Check", "GET", "health", 200)

    def test_authentication_flows(self):
        """Test all authentication flows"""
        print("\n" + "="*50)
        print("TESTING AUTHENTICATION")
        print("="*50)
        
        # Test all user logins
        login_results = {}
        for user_type in self.credentials.keys():
            login_results[user_type] = self.login_user(user_type)
        
        # Test /auth/me endpoint for authenticated users
        for user_type, logged_in in login_results.items():
            if logged_in:
                self.test_authenticated_endpoint(user_type, f"Get {user_type} profile", "GET", "auth/me")
        
        return login_results

    def test_tenant_operations(self, login_results: Dict):
        """Test tenant-related operations"""
        print("\n" + "="*50)
        print("TESTING TENANT OPERATIONS")
        print("="*50)
        
        if login_results.get("super_admin"):
            # List all tenants
            self.test_authenticated_endpoint("super_admin", "List tenants", "GET", "tenants")
            
            # Get tenant by slug (public endpoint)
            self.run_test("Get Aurum tenant by slug", "GET", "tenants/slug/aurumbet", 200)
            self.run_test("Get BlueWave tenant by slug", "GET", "tenants/slug/bluewave", 200)

    def test_user_operations(self, login_results: Dict):
        """Test user/player operations"""
        print("\n" + "="*50)
        print("TESTING USER OPERATIONS") 
        print("="*50)
        
        # Super admin can list all users
        if login_results.get("super_admin"):
            self.test_authenticated_endpoint("super_admin", "List all users", "GET", "users")
            
        # Tenant admin can list tenant users
        if login_results.get("tenant_admin_aurum"):
            self.test_authenticated_endpoint("tenant_admin_aurum", "List tenant players", "GET", "users?role=player")

    def test_game_operations(self, login_results: Dict):
        """Test game-related operations"""
        print("\n" + "="*50)
        print("TESTING GAME OPERATIONS")
        print("="*50)
        
        games_data = {}
        
        # Test game listing for different users
        for user_type in ["super_admin", "tenant_admin_aurum", "player_aurum"]:
            if login_results.get(user_type):
                success, data = self.test_authenticated_endpoint(user_type, f"List games as {user_type}", "GET", "games")
                if success and isinstance(data, list) and len(data) > 0:
                    games_data[user_type] = data[0]['id']  # Store first game ID
        
        # Test game launch for player
        if login_results.get("player_aurum") and games_data.get("player_aurum"):
            game_id = games_data["player_aurum"]
            success, session_data = self.test_authenticated_endpoint(
                "player_aurum", 
                "Launch game", 
                "POST", 
                f"games/{game_id}/launch"
            )
            
            # Test game spin if launch successful
            if success and 'session_id' in session_data:
                spin_data = {
                    "session_id": session_data['session_id'],
                    "bet_amount": 1.0
                }
                self.test_authenticated_endpoint(
                    "player_aurum",
                    "Game spin",
                    "POST", 
                    "games/spin",
                    data=spin_data
                )

    def test_wallet_operations(self, login_results: Dict):
        """Test wallet and deposit operations"""
        print("\n" + "="*50)
        print("TESTING WALLET OPERATIONS")
        print("="*50)
        
        if login_results.get("player_aurum"):
            # Get wallet balance
            self.test_authenticated_endpoint("player_aurum", "Get wallet balance", "GET", "wallet/balance")
            
            # Test deposit
            deposit_data = {"amount": 50.0}
            self.test_authenticated_endpoint("player_aurum", "Wallet deposit", "POST", "wallet/deposit", data=deposit_data)

    def test_transaction_operations(self, login_results: Dict):
        """Test transaction listing"""
        print("\n" + "="*50)
        print("TESTING TRANSACTION OPERATIONS")
        print("="*50)
        
        # Test for different user types
        for user_type in ["super_admin", "tenant_admin_aurum", "player_aurum"]:
            if login_results.get(user_type):
                self.test_authenticated_endpoint(user_type, f"List transactions as {user_type}", "GET", "transactions")

    def test_stats_operations(self, login_results: Dict):
        """Test statistics endpoints"""
        print("\n" + "="*50)
        print("TESTING STATISTICS OPERATIONS")
        print("="*50)
        
        if login_results.get("super_admin"):
            self.test_authenticated_endpoint("super_admin", "Global stats", "GET", "stats/global")
            
        if login_results.get("tenant_admin_aurum"):
            # Need to get tenant_id first, let's use a known pattern
            # Assuming tenant ID pattern, we'll test with a placeholder
            pass  # Skip tenant stats for now as we'd need tenant ID

    def run_all_tests(self):
        """Run comprehensive test suite"""
        print(f"\n{'='*60}")
        print("GAMING PLATFORM API TEST SUITE")
        print(f"Backend URL: {self.base_url}")
        print(f"{'='*60}")
        
        try:
            # Test basic endpoints
            self.test_health_endpoints()
            
            # Test authentication
            login_results = self.test_authentication_flows()
            
            # Test core functionality if authentication works
            if any(login_results.values()):
                self.test_tenant_operations(login_results)
                self.test_user_operations(login_results)
                self.test_game_operations(login_results)
                self.test_wallet_operations(login_results)
                self.test_transaction_operations(login_results)
                self.test_stats_operations(login_results)
            else:
                print("\n❌ No successful logins - skipping authenticated tests")
                
        except Exception as e:
            print(f"\n❌ Test suite failed with error: {str(e)}")

        # Print summary
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}")
        print(f"📊 Tests passed: {self.tests_passed}/{self.tests_run}")
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"📈 Success rate: {success_rate:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return 0
        else:
            print("⚠️  Some tests failed")
            return 1

def main():
    tester = GamingPlatformTester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())