#!/usr/bin/env python3
import requests
import sys
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

class SeamlessIntegrationTester:
    def __init__(self, base_url="https://games-polish-mobile.preview.emergentagent.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.tests_run = 0
        self.tests_passed = 0
        self.auth_cookies = {}
        
        # Real imported game ID from review request
        self.real_game_id = "375c90ef-f0e9-5a5b-ae47-87008cca79e3"
        
        # Live MORRISLITA credentials from review request
        self.callback_auth = {
            "agent_code": "MORRISLITA",
            "agent_secret": "72c169eb6d124a58f7e62ad6f4bf72cb"
        }
        
        # Player credentials
        self.player_creds = {
            "email": "player1@aurumbet.demo",
            "password": "player123",
            "tenant_slug": "aurumbet"
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
                    print(f"   Response: {response.text[:500]}")

            try:
                response_data = response.json() if response.text else {}
            except:
                response_data = {"raw_response": response.text}

            return success, response_data

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {"error": str(e)}

    def login_player(self) -> bool:
        """Login player and store auth cookies"""
        login_data = {
            "email": self.player_creds["email"], 
            "password": self.player_creds["password"],
            "tenant_slug": self.player_creds["tenant_slug"]
        }
        
        success, response = self.run_test(
            "Player Login",
            "POST",
            "auth/login",
            200,
            data=login_data
        )
        
        if success and 'access_token' in response:
            self.auth_cookies = self.session.cookies.get_dict()
            print(f"   ✅ Player logged in: {response.get('user', {}).get('email', 'unknown')}")
            return True
        return False

    def test_game_launch(self) -> bool:
        """Test POST /api/games/{game_id}/launch for real imported game"""
        print("\n" + "="*60)
        print("TESTING SEAMLESS GAME LAUNCH")
        print("="*60)
        
        success, launch_data = self.run_test(
            f"Launch Real Game (Chin Shi Huang) - ID: {self.real_game_id}",
            "POST",
            f"games/{self.real_game_id}/launch",
            200,
            cookies=self.auth_cookies
        )
        
        if success:
            print(f"   ✅ Launch URL received: {launch_data.get('launch_url', 'No URL')[:100]}...")
            if 'session_id' in launch_data:
                print(f"   ✅ Session ID: {launch_data['session_id']}")
            return True
        else:
            print(f"   ❌ Launch failed for game {self.real_game_id}")
            return False

    def test_enriched_games_api(self) -> bool:
        """Test GET /api/games returns enriched games with source API thumbnails"""
        print("\n" + "="*60)
        print("TESTING ENRICHED GAMES API")
        print("="*60)
        
        success, games_data = self.run_test(
            "Get Enriched Games List",
            "GET",
            "games",
            200,
            cookies=self.auth_cookies
        )
        
        if success and isinstance(games_data, list):
            enriched_count = 0
            thumbnail_count = 0
            banner_count = 0
            
            for game in games_data[:20]:  # Check first 20 games
                if game.get('live_provider_code') or game.get('launch_provider_code'):
                    enriched_count += 1
                if game.get('thumbnail_url'):
                    thumbnail_count += 1
                if game.get('source_banner_url'):
                    banner_count += 1
            
            print(f"   ✅ Total games: {len(games_data)}")
            print(f"   ✅ Games with live provider codes: {enriched_count}")
            print(f"   ✅ Games with thumbnails: {thumbnail_count}")
            print(f"   ✅ Games with source banner URLs: {banner_count}")
            
            # Look for the specific Chin Shi Huang game
            chin_shi_game = None
            for game in games_data:
                if game.get('id') == self.real_game_id:
                    chin_shi_game = game
                    break
            
            if chin_shi_game:
                print(f"   ✅ Found Chin Shi Huang game:")
                print(f"      - Name: {chin_shi_game.get('name', 'Unknown')}")
                print(f"      - Provider: {chin_shi_game.get('provider_name', 'Unknown')}")
                print(f"      - Live provider code: {chin_shi_game.get('live_provider_code', 'None')}")
                print(f"      - Launch game code: {chin_shi_game.get('launch_game_code', 'None')}")
                print(f"      - Thumbnail URL: {chin_shi_game.get('thumbnail_url', 'None')}")
                return True
            else:
                print(f"   ❌ Chin Shi Huang game not found in games list")
                return False
        else:
            print(f"   ❌ Failed to get games list or invalid response format")
            return False

    def test_user_balance_callback(self) -> bool:
        """Test POST /gold_api/user_balance with live MORRISLITA credentials"""
        print("\n" + "="*60)
        print("TESTING USER BALANCE CALLBACK")
        print("="*60)
        
        callback_data = {
            "agent_code": self.callback_auth["agent_code"],
            "agent_secret": self.callback_auth["agent_secret"],
            "user_code": "player_aurumbet_001"  # Correct player ID for aurumbet tenant
        }
        
        success, response = self.run_test(
            "User Balance Callback",
            "POST",
            "gold_api/user_balance",
            200,
            data=callback_data
        )
        
        if success:
            print(f"   ✅ Status: {response.get('status', 'Unknown')}")
            print(f"   ✅ User balance: {response.get('user_balance', 'Unknown')}")
            return True
        return False

    def test_game_callback_idempotency(self) -> bool:
        """Test POST /gold_api/game_callback idempotency with MORRISLITA credentials"""
        print("\n" + "="*60)
        print("TESTING GAME CALLBACK IDEMPOTENCY")
        print("="*60)
        
        # Generate unique transaction ID
        txn_id = f"test_game_txn_{int(time.time())}"
        
        callback_data = {
            "agent_code": self.callback_auth["agent_code"],
            "agent_secret": self.callback_auth["agent_secret"],
            "agent_balance": 1000000.0,
            "user_code": "player_aurumbet_001",
            "user_balance": 50000.0,
            "user_total_credit": 0.0,
            "user_total_debit": 100.0,
            "game_type": "slot",
            "slot": {
                "provider_code": "JILI",
                "game_code": "2",
                "round_id": f"test_round_{int(time.time())}",
                "is_round_finished": True,
                "type": "BASE",
                "bet": 100.0,
                "win": 50.0,
                "txn_id": txn_id,
                "txn_type": "debit_credit",
                "user_before_balance": 50000.0,
                "user_after_balance": 49950.0,
                "created_at": datetime.now().isoformat()
            }
        }
        
        # First call
        success1, response1 = self.run_test(
            "Game Callback - First Call",
            "POST",
            "gold_api/game_callback",
            200,
            data=callback_data
        )
        
        # Second call (should be idempotent)
        success2, response2 = self.run_test(
            "Game Callback - Second Call (Idempotent)",
            "POST",
            "gold_api/game_callback",
            200,
            data=callback_data
        )
        
        if success1 and success2:
            print(f"   ✅ First call status: {response1.get('status', 'Unknown')}")
            print(f"   ✅ Second call status: {response2.get('status', 'Unknown')}")
            print(f"   ✅ Idempotent flag: {response2.get('idempotent', False)}")
            return True
        return False

    def test_money_callback_idempotency(self) -> bool:
        """Test POST /gold_api/money_callback idempotency with MORRISLITA credentials"""
        print("\n" + "="*60)
        print("TESTING MONEY CALLBACK IDEMPOTENCY")
        print("="*60)
        
        timestamp = datetime.now().isoformat()
        callback_data = {
            "agent_code": self.callback_auth["agent_code"],
            "agent_secret": self.callback_auth["agent_secret"],
            "agent_type": "Seamless",
            "user_code": "player_aurumbet_001",
            "provider_code": "JILI",
            "game_code": "2",
            "type": "credit",
            "agent_before_balance": 1000000.0,
            "agent_after_balance": 999900.0,
            "user_before_balance": 50000.0,
            "user_after_balance": 50100.0,
            "amount": 100.0,
            "msg": "Test deposit",
            "created_at": timestamp
        }
        
        # First call
        success1, response1 = self.run_test(
            "Money Callback - First Call",
            "POST",
            "gold_api/money_callback",
            200,
            data=callback_data
        )
        
        # Second call (should be idempotent)
        success2, response2 = self.run_test(
            "Money Callback - Second Call (Idempotent)",
            "POST",
            "gold_api/money_callback",
            200,
            data=callback_data
        )
        
        if success1 and success2:
            print(f"   ✅ First call status: {response1.get('status', 'Unknown')}")
            print(f"   ✅ Second call status: {response2.get('status', 'Unknown')}")
            print(f"   ✅ Idempotent flag: {response2.get('idempotent', False)}")
            return True
        return False

    def test_providers_api(self) -> bool:
        """Test providers API for branding checks"""
        print("\n" + "="*60)
        print("TESTING PROVIDERS API (BRANDING CHECK)")
        print("="*60)
        
        success, providers_data = self.run_test(
            "Get Providers List",
            "GET",
            "providers",
            200,
            cookies=self.auth_cookies
        )
        
        if success and isinstance(providers_data, list):
            egs_vd7_count = 0
            seamless_count = 0
            
            for provider in providers_data:
                name = (provider.get('name', '') or '').upper()
                code = (provider.get('code', '') or '').upper()
                
                if 'EGS' in name or 'VD7' in name or 'EGS' in code or 'VD7' in code:
                    egs_vd7_count += 1
                    print(f"   ⚠️  Found EGS/VD7 provider: {provider.get('name', 'Unknown')} ({provider.get('code', 'Unknown')})")
                
                if 'SEAMLESS' in name or 'SEAMLESS' in code:
                    seamless_count += 1
            
            print(f"   ✅ Total providers: {len(providers_data)}")
            print(f"   ✅ Seamless providers: {seamless_count}")
            
            if egs_vd7_count > 0:
                print(f"   ⚠️  EGS/VD7 branding found in {egs_vd7_count} providers - may need review")
            else:
                print(f"   ✅ No EGS/VD7 branding leaks found")
            
            return True
        return False

    def run_seamless_integration_tests(self):
        """Run comprehensive seamless integration test suite"""
        print(f"\n{'='*80}")
        print("SEAMLESS INTEGRATION TEST SUITE")
        print(f"Backend URL: {self.base_url}")
        print(f"Real Game ID: {self.real_game_id}")
        print(f"Agent Code: {self.callback_auth['agent_code']}")
        print(f"{'='*80}")
        
        test_results = {}
        
        try:
            # Login player first
            if not self.login_player():
                print("\n❌ Player login failed - cannot continue with authenticated tests")
                return 1
            
            # Test seamless integration features
            test_results['game_launch'] = self.test_game_launch()
            test_results['enriched_games'] = self.test_enriched_games_api()
            test_results['user_balance'] = self.test_user_balance_callback()
            test_results['game_callback'] = self.test_game_callback_idempotency()
            test_results['money_callback'] = self.test_money_callback_idempotency()
            test_results['providers_branding'] = self.test_providers_api()
            
        except Exception as e:
            print(f"\n❌ Test suite failed with error: {str(e)}")
            return 1

        # Print summary
        print(f"\n{'='*80}")
        print("SEAMLESS INTEGRATION TEST SUMMARY")
        print(f"{'='*80}")
        print(f"📊 Tests passed: {self.tests_passed}/{self.tests_run}")
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"📈 Success rate: {success_rate:.1f}%")
        
        print(f"\n🔍 Feature Test Results:")
        for feature, passed in test_results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   {feature}: {status}")
        
        all_features_passed = all(test_results.values())
        
        if self.tests_passed == self.tests_run and all_features_passed:
            print("\n🎉 All seamless integration tests passed!")
            return 0
        else:
            print("\n⚠️  Some tests failed - see details above")
            return 1

def main():
    tester = SeamlessIntegrationTester()
    return tester.run_seamless_integration_tests()

if __name__ == "__main__":
    sys.exit(main())