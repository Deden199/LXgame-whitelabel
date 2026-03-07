#!/usr/bin/env python3
import requests
import sys
import json
from datetime import datetime

class SpecificFeatureTester:
    def __init__(self, base_url="https://games-polish-mobile.preview.emergentagent.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.auth_tokens = {}
        
        # Test credentials
        self.credentials = {
            "super_admin": {"email": "admin@platform.com", "password": "admin123"},
            "tenant_admin_aurum": {"email": "admin@aurumbet.com", "password": "admin123"},
            "player_aurum": {"email": "player1@aurumbet.demo", "password": "player123", "tenant_slug": "aurumbet"}
        }

    def login_user(self, user_type: str) -> bool:
        """Login a user and store cookies"""
        creds = self.credentials[user_type]
        login_data = {
            "email": creds["email"], 
            "password": creds["password"]
        }
        
        if "tenant_slug" in creds:
            login_data["tenant_slug"] = creds["tenant_slug"]
        
        url = f"{self.base_url}/api/auth/login"
        response = self.session.post(url, json=login_data)
        
        if response.status_code == 200:
            self.auth_tokens[user_type] = self.session.cookies.get_dict()
            print(f"✅ {user_type} login successful")
            return True
        else:
            print(f"❌ {user_type} login failed: {response.status_code}")
            return False

    def test_endpoint(self, name: str, endpoint: str, user_type: str = "player_aurum", params: dict = None):
        """Test a specific endpoint"""
        url = f"{self.base_url}/api/{endpoint.lstrip('/')}"
        cookies = self.auth_tokens.get(user_type, {})
        
        try:
            response = self.session.get(url, cookies=cookies, params=params)
            print(f"\n🔍 Testing {name}:")
            print(f"   Endpoint: GET {endpoint}")
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    print(f"   Response: List with {len(data)} items")
                    if len(data) > 0 and isinstance(data[0], dict):
                        print(f"   Sample item keys: {list(data[0].keys())}")
                elif isinstance(data, dict):
                    print(f"   Response keys: {list(data.keys())}")
                return True, data
            else:
                print(f"   Error: {response.text[:100]}")
                return False, {}
        except Exception as e:
            print(f"   Exception: {str(e)}")
            return False, {}

    def test_player_features(self):
        """Test player-specific features"""
        print("\n" + "="*60)
        print("TESTING PLAYER DASHBOARD FEATURES")
        print("="*60)
        
        # Test player stats
        success, stats = self.test_endpoint("Player Stats", "player/stats", "player_aurum")
        if success:
            print(f"   Stats data: {json.dumps(stats, indent=2)}")
        
        # Test recent games
        success, recent_games = self.test_endpoint("Recent Games", "player/recent-games", "player_aurum")
        if success:
            print(f"   Recent games count: {len(recent_games) if isinstance(recent_games, list) else 'Not a list'}")
        
        # Test transactions
        success, transactions = self.test_endpoint("Player Transactions", "transactions", "player_aurum", {"limit": 5})
        if success:
            print(f"   Recent transactions count: {len(transactions) if isinstance(transactions, list) else 'Not a list'}")

    def test_game_features(self):
        """Test game-related features"""
        print("\n" + "="*60)
        print("TESTING GAME FEATURES")
        print("="*60)
        
        # Test games listing
        success, games = self.test_endpoint("All Games", "games", "player_aurum")
        if success and isinstance(games, list):
            print(f"   Total games: {len(games)}")
            if len(games) > 0:
                # Check categories and tags
                categories = set()
                tags = set()
                for game in games:
                    if 'category' in game:
                        categories.add(game['category'])
                    if 'tags' in game and isinstance(game['tags'], list):
                        tags.update(game['tags'])
                
                print(f"   Categories: {sorted(categories)}")
                print(f"   Tags: {sorted(tags)}")
        
        # Test game categories
        success, categories = self.test_endpoint("Game Categories", "games/categories", "player_aurum")
        if success:
            print(f"   Categories data: {json.dumps(categories, indent=2)}")
        
        # Test filtering by category
        success, slots_games = self.test_endpoint("Slots Games", "games", "player_aurum", {"category": "slots"})
        if success and isinstance(slots_games, list):
            print(f"   Slots games: {len(slots_games)}")
        
        # Test filtering by tag  
        success, popular_games = self.test_endpoint("Popular Games", "games", "player_aurum", {"tag": "popular"})
        if success and isinstance(popular_games, list):
            print(f"   Popular games: {len(popular_games)}")

    def test_wallet_features(self):
        """Test wallet and withdrawal features"""
        print("\n" + "="*60)
        print("TESTING WALLET FEATURES")
        print("="*60)
        
        # Test wallet balance
        success, balance = self.test_endpoint("Wallet Balance", "wallet/balance", "player_aurum")
        if success:
            print(f"   Balance data: {json.dumps(balance, indent=2)}")
        
        # Test withdrawal (POST request)
        url = f"{self.base_url}/api/wallet/withdraw"
        cookies = self.auth_tokens.get("player_aurum", {})
        
        try:
            response = self.session.post(url, json={"amount": 25.0}, cookies=cookies)
            print(f"\n🔍 Testing Withdrawal:")
            print(f"   Endpoint: POST wallet/withdraw")
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   Response: {json.dumps(data, indent=2)}")
            else:
                print(f"   Error: {response.text[:100]}")
        except Exception as e:
            print(f"   Exception: {str(e)}")

    def test_admin_features(self):
        """Test admin features"""
        print("\n" + "="*60)
        print("TESTING ADMIN FEATURES")
        print("="*60)
        
        # Super Admin stats
        success, global_stats = self.test_endpoint("Global Stats", "stats/global", "super_admin")
        if success:
            print(f"   Global stats: {json.dumps(global_stats, indent=2)}")
            # Check if we have 8 stat categories
            expected_stats = ['total_tenants', 'total_players', 'total_games', 'total_transactions', 
                            'total_deposits', 'total_bets', 'total_wins', 'total_volume']
            present_stats = [key for key in expected_stats if key in global_stats]
            print(f"   Expected 8 stat cards, found: {len(present_stats)} - {present_stats}")
        
        # Tenant listing with stats
        success, tenants = self.test_endpoint("Tenants List", "tenants", "super_admin")
        if success and isinstance(tenants, list):
            print(f"   Total tenants: {len(tenants)}")
            if len(tenants) > 0:
                print(f"   Sample tenant keys: {list(tenants[0].keys())}")
        
        # Tenant admin features
        success, tenant_players = self.test_endpoint("Tenant Players", "users?role=player", "tenant_admin_aurum")
        if success and isinstance(tenant_players, list):
            print(f"   Tenant players: {len(tenant_players)}")
            if len(tenant_players) > 0:
                player = tenant_players[0]
                print(f"   Sample player data keys: {list(player.keys())}")
                expected_fields = ['wallet_balance', 'total_bets', 'last_login']
                present_fields = [key for key in expected_fields if key in player]
                print(f"   Player stats fields found: {present_fields}")

    def run_specific_tests(self):
        """Run specific feature tests"""
        print(f"\n{'='*60}")
        print("GAMING PLATFORM SPECIFIC FEATURE TESTS")
        print(f"Backend URL: {self.base_url}")
        print(f"{'='*60}")
        
        # Login users
        print("Logging in test users...")
        for user_type in ["super_admin", "tenant_admin_aurum", "player_aurum"]:
            self.login_user(user_type)
        
        # Run feature tests
        self.test_player_features()
        self.test_game_features() 
        self.test_wallet_features()
        self.test_admin_features()
        
        print(f"\n{'='*60}")
        print("SPECIFIC FEATURE TESTS COMPLETED")
        print(f"{'='*60}")

def main():
    tester = SpecificFeatureTester()
    tester.run_specific_tests()
    return 0

if __name__ == "__main__":
    sys.exit(main())