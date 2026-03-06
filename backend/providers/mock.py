from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import uuid
import random

from .base import GameProviderAdapter


class MockProviderAdapter(GameProviderAdapter):
    """
    Mock provider adapter for demonstration and testing.
    Simulates a real game provider integration.
    """
    
    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}
    
    @property
    def provider_id(self) -> str:
        return "mock"
    
    @property
    def provider_name(self) -> str:
        return "Mock Provider (Demo)"
    
    async def create_session(
        self,
        player_id: str,
        game_id: str,
        tenant_id: str,
        currency: str = "USD",
        language: str = "en",
        **kwargs
    ) -> Dict[str, Any]:
        """Create a mock game session"""
        session_id = f"mock_session_{uuid.uuid4().hex[:16]}"
        expires_at = datetime.now(timezone.utc) + timedelta(hours=2)
        
        # Store session data
        self._sessions[session_id] = {
            "session_id": session_id,
            "player_id": player_id,
            "game_id": game_id,
            "tenant_id": tenant_id,
            "currency": currency,
            "language": language,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": expires_at.isoformat(),
            "status": "active",
            "rounds": []
        }
        
        # Generate mock launch URL
        launch_url = f"/game-simulator?session={session_id}&game={game_id}"
        
        return {
            "session_id": session_id,
            "launch_url": launch_url,
            "expires_at": expires_at
        }
    
    async def get_launch_url(self, session_id: str) -> str:
        """Get launch URL for existing session"""
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        return f"/game-simulator?session={session_id}&game={session['game_id']}"
    
    async def handle_callback(
        self,
        action: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle mock provider callbacks.
        In production, this would process real game events.
        """
        session_id = payload.get("session_id")
        amount = payload.get("amount", 0)
        round_id = payload.get("round_id", str(uuid.uuid4()))
        
        session = self._sessions.get(session_id)
        if not session:
            return {
                "success": False,
                "error": "Session not found",
                "balance": 0
            }
        
        # Record the round action
        round_action = {
            "round_id": round_id,
            "action": action,
            "amount": amount,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        session["rounds"].append(round_action)
        
        # Mock response - in reality, this would interact with the wallet
        return {
            "success": True,
            "balance": payload.get("current_balance", 0) - amount if action == "bet" else payload.get("current_balance", 0) + amount,
            "tx_id": f"mock_tx_{uuid.uuid4().hex[:12]}"
        }
    
    async def validate_session(self, session_id: str) -> bool:
        """Check if session is valid"""
        session = self._sessions.get(session_id)
        if not session:
            return False
        
        if session["status"] != "active":
            return False
        
        expires_at = datetime.fromisoformat(session["expires_at"])
        if datetime.now(timezone.utc) > expires_at:
            session["status"] = "expired"
            return False
        
        return True
    
    async def close_session(self, session_id: str) -> bool:
        """Close a game session"""
        session = self._sessions.get(session_id)
        if not session:
            return False
        
        session["status"] = "closed"
        session["closed_at"] = datetime.now(timezone.utc).isoformat()
        return True
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information (for debugging/demo)"""
        return self._sessions.get(session_id)
    
    async def simulate_spin(
        self,
        session_id: str,
        bet_amount: float,
        current_balance: float
    ) -> Dict[str, Any]:
        """
        Simulate a slot spin for demo purposes.
        Returns bet and potential win results.
        """
        if not await self.validate_session(session_id):
            return {"success": False, "error": "Invalid session"}
        
        round_id = f"round_{uuid.uuid4().hex[:12]}"
        
        # Simulate RNG - roughly 45% win rate, with varying multipliers
        win_chance = random.random()
        
        if win_chance < 0.45:  # Win
            # Determine multiplier
            mult_roll = random.random()
            if mult_roll < 0.7:  # Small win (1-2x)
                multiplier = random.uniform(1.0, 2.0)
            elif mult_roll < 0.9:  # Medium win (2-5x)
                multiplier = random.uniform(2.0, 5.0)
            elif mult_roll < 0.98:  # Big win (5-20x)
                multiplier = random.uniform(5.0, 20.0)
            else:  # Jackpot (20-100x)
                multiplier = random.uniform(20.0, 100.0)
            
            win_amount = round(bet_amount * multiplier, 2)
            result = "win"
        else:  # Loss
            win_amount = 0
            multiplier = 0
            result = "loss"
        
        new_balance = current_balance - bet_amount + win_amount
        
        return {
            "success": True,
            "round_id": round_id,
            "bet_amount": bet_amount,
            "win_amount": win_amount,
            "multiplier": round(multiplier, 2),
            "result": result,
            "balance_before": current_balance,
            "balance_after": round(new_balance, 2),
            "symbols": self._generate_symbols(result, multiplier)
        }
    
    def _generate_symbols(self, result: str, multiplier: float) -> list:
        """Generate mock slot symbols for display"""
        symbols = ["🍒", "🍋", "🍊", "🍇", "⭐", "💎", "7️⃣", "🎰"]
        
        if result == "win":
            if multiplier >= 20:
                # Jackpot - all same
                symbol = random.choice(["💎", "7️⃣", "🎰"])
                return [[symbol, symbol, symbol] for _ in range(3)]
            elif multiplier >= 5:
                # Big win - row match
                symbol = random.choice(symbols)
                grid = [[random.choice(symbols) for _ in range(3)] for _ in range(3)]
                grid[1] = [symbol, symbol, symbol]
                return grid
            else:
                # Small win - diagonal or partial
                grid = [[random.choice(symbols) for _ in range(3)] for _ in range(3)]
                symbol = random.choice(symbols)
                grid[0][0] = grid[1][1] = grid[2][2] = symbol
                return grid
        else:
            # Loss - random
            return [[random.choice(symbols) for _ in range(3)] for _ in range(3)]


# Placeholder adapters for future providers
class PragmaticPlayAdapter(GameProviderAdapter):
    """Placeholder for Pragmatic Play integration"""
    
    @property
    def provider_id(self) -> str:
        return "pragmatic"
    
    @property
    def provider_name(self) -> str:
        return "Pragmatic Play"
    
    async def create_session(self, *args, **kwargs):
        raise NotImplementedError("Pragmatic Play integration pending")
    
    async def get_launch_url(self, session_id: str):
        raise NotImplementedError("Pragmatic Play integration pending")
    
    async def handle_callback(self, action: str, payload):
        raise NotImplementedError("Pragmatic Play integration pending")
    
    async def validate_session(self, session_id: str):
        raise NotImplementedError("Pragmatic Play integration pending")
    
    async def close_session(self, session_id: str):
        raise NotImplementedError("Pragmatic Play integration pending")


class PGSoftAdapter(GameProviderAdapter):
    """Placeholder for PGSoft integration"""
    
    @property
    def provider_id(self) -> str:
        return "pgsoft"
    
    @property
    def provider_name(self) -> str:
        return "PGSoft"
    
    async def create_session(self, *args, **kwargs):
        raise NotImplementedError("PGSoft integration pending")
    
    async def get_launch_url(self, session_id: str):
        raise NotImplementedError("PGSoft integration pending")
    
    async def handle_callback(self, action: str, payload):
        raise NotImplementedError("PGSoft integration pending")
    
    async def validate_session(self, session_id: str):
        raise NotImplementedError("PGSoft integration pending")
    
    async def close_session(self, session_id: str):
        raise NotImplementedError("PGSoft integration pending")
