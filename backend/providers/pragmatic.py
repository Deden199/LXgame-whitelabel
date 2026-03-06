"""
Pragmatic Play Provider Adapter

This adapter implements the Seamless Wallet integration pattern for Pragmatic Play.

INTEGRATION REQUIREMENTS:
- Valid Pragmatic Play commercial contract
- API credentials from Pragmatic integration portal
- Registered callback URLs with Pragmatic

See /docs/PROVIDERS.md for complete integration guide.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import os
import hmac
import hashlib
import httpx
import logging

from .base import GameProviderAdapter

logger = logging.getLogger(__name__)


class PragmaticPlayAdapter(GameProviderAdapter):
    """
    Pragmatic Play Seamless Wallet adapter.
    
    Required environment variables:
    - PRAGMATIC_API_URL: API endpoint (sandbox or production)
    - PRAGMATIC_SECRET_KEY: HMAC signing key for hash verification
    - PRAGMATIC_CASINO_ID: Your casino/operator identifier
    
    Pragmatic Play uses a Seamless Wallet model where they call OUR endpoints
    for balance checks and transactions. We call THEIR endpoints only for:
    - Game launch URL generation
    - Game catalog synchronization
    """
    
    def __init__(self):
        self.api_url = os.environ.get('PRAGMATIC_API_URL', '')
        self.secret_key = os.environ.get('PRAGMATIC_SECRET_KEY', '')
        self.casino_id = os.environ.get('PRAGMATIC_CASINO_ID', '')
        self._configured = bool(self.api_url and self.secret_key and self.casino_id)
        
        if self._configured:
            logger.info("Pragmatic Play adapter initialized with credentials")
        else:
            logger.warning("Pragmatic Play adapter not configured - missing credentials")
    
    @property
    def provider_id(self) -> str:
        return "pragmatic"
    
    @property
    def provider_name(self) -> str:
        return "Pragmatic Play"
    
    @property
    def is_configured(self) -> bool:
        """Check if provider credentials are configured"""
        return self._configured
    
    # =========================================================================
    # HASH SIGNATURE METHODS
    # =========================================================================
    
    def generate_hash(self, params: Dict[str, Any]) -> str:
        """
        Generate HMAC-MD5 hash for outgoing API requests.
        
        TODO: Confirm exact hash composition with Pragmatic documentation.
        Common pattern: userId + timestamp + gameId + roundId + secretKey
        """
        # This is a placeholder - exact format from Pragmatic docs
        hash_string = ''.join([
            str(params.get('userId', '')),
            str(params.get('timestamp', '')),
            str(params.get('gameId', '')),
            str(params.get('roundId', '')),
            self.secret_key
        ])
        
        return hmac.new(
            self.secret_key.encode('utf-8'),
            hash_string.encode('utf-8'),
            hashlib.md5
        ).hexdigest()
    
    def verify_callback_hash(self, params: Dict[str, Any], received_hash: str) -> bool:
        """
        Verify HMAC hash from Pragmatic Play callback.
        
        Args:
            params: Callback parameters (without hash)
            received_hash: Hash value from callback
            
        Returns:
            True if hash is valid
        """
        expected_hash = self.generate_hash(params)
        return hmac.compare_digest(expected_hash, received_hash)
    
    # =========================================================================
    # SESSION MANAGEMENT
    # =========================================================================
    
    async def create_session(
        self,
        player_id: str,
        game_id: str,
        tenant_id: str,
        currency: str = "USD",
        language: str = "en",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a game session with Pragmatic Play.
        
        This requests a game launch URL from Pragmatic. The actual game
        session is established when the player opens the URL and Pragmatic
        calls our /authenticate endpoint.
        
        Args:
            player_id: Our internal player ID
            game_id: Pragmatic game symbol (e.g., "vs50hercules")
            tenant_id: Tenant identifier for multi-tenant support
            currency: Player's currency code
            language: UI language code
            
        Returns:
            {
                "session_id": str,      # Our internal session tracking ID
                "launch_url": str,      # URL to open game
                "expires_at": datetime  # Session expiry
            }
        """
        if not self._configured:
            raise NotImplementedError(
                "Pragmatic Play adapter not configured. "
                "Set PRAGMATIC_API_URL, PRAGMATIC_SECRET_KEY, and PRAGMATIC_CASINO_ID "
                "in backend/.env"
            )
        
        # Generate our session token that Pragmatic will send back on callbacks
        import uuid
        session_token = f"pp_{tenant_id}_{player_id}_{uuid.uuid4().hex[:12]}"
        timestamp = int(datetime.now(timezone.utc).timestamp())
        
        # TODO: Implement actual API call to Pragmatic
        # =====================================================================
        # EXAMPLE IMPLEMENTATION (not production-ready):
        #
        # request_params = {
        #     "casinoId": self.casino_id,
        #     "userId": player_id,
        #     "gameSymbol": game_id,
        #     "currency": currency,
        #     "language": language,
        #     "token": session_token,  # Our session token
        #     "platform": kwargs.get("platform", "WEB"),
        #     "lobbyUrl": kwargs.get("lobby_url", ""),
        #     "timestamp": timestamp
        # }
        # request_params["hash"] = self.generate_hash(request_params)
        #
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(
        #         f"{self.api_url}/IntegrationService/v3/http/CasinoGameAPI/game/start",
        #         data=request_params,
        #         timeout=10.0
        #     )
        #     
        #     if response.status_code != 200:
        #         logger.error(f"Pragmatic API error: {response.text}")
        #         raise Exception("Failed to create game session")
        #     
        #     data = response.json()
        #     
        #     if data.get("error") != 0:
        #         raise Exception(f"Pragmatic error: {data.get('description')}")
        #     
        #     return {
        #         "session_id": session_token,
        #         "launch_url": data["gameURL"],
        #         "expires_at": datetime.now(timezone.utc) + timedelta(hours=2)
        #     }
        # =====================================================================
        
        raise NotImplementedError(
            "Pragmatic Play create_session not yet implemented. "
            "See /docs/PROVIDERS.md for integration guide."
        )
    
    async def get_launch_url(self, session_id: str) -> str:
        """
        Get launch URL for an existing session.
        
        Note: Pragmatic sessions are typically one-use. If the player
        needs to re-enter a game, create a new session instead.
        """
        if not self._configured:
            raise NotImplementedError("Pragmatic Play adapter not configured")
        
        # TODO: Implement if Pragmatic supports retrieving existing session URLs
        raise NotImplementedError(
            "Pragmatic Play get_launch_url not implemented. "
            "Create a new session instead."
        )
    
    # =========================================================================
    # CALLBACK HANDLING
    # =========================================================================
    
    async def handle_callback(
        self,
        action: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle Pragmatic Play callbacks.
        
        This is the main entry point for processing Pragmatic callbacks.
        Each callback type has specific handling requirements.
        
        Args:
            action: Callback type - "authenticate", "balance", "bet", "result", "refund"
            payload: Callback data from Pragmatic
            
        Returns:
            Response dict matching Pragmatic's expected format:
            {
                "error": 0,           # Error code (0 = success)
                "description": "...", # Error/success message
                "balance": 10000,     # Current balance (in smallest currency unit)
                "currency": "USD"     # Currency code
            }
        """
        if not self._configured:
            return {
                "error": 100,
                "description": "Provider not configured"
            }
        
        # Verify hash before processing
        received_hash = payload.pop("hash", "")
        if not self.verify_callback_hash(payload, received_hash):
            logger.warning(f"Invalid hash in Pragmatic {action} callback")
            return {
                "error": 3,
                "description": "Invalid hash"
            }
        
        # Route to specific handler
        handlers = {
            "authenticate": self._handle_authenticate,
            "balance": self._handle_balance,
            "bet": self._handle_bet,
            "result": self._handle_result,
            "refund": self._handle_refund,
        }
        
        handler = handlers.get(action)
        if not handler:
            logger.error(f"Unknown Pragmatic callback action: {action}")
            return {
                "error": 100,
                "description": f"Unknown action: {action}"
            }
        
        try:
            return await handler(payload)
        except Exception as e:
            logger.exception(f"Error handling Pragmatic {action} callback: {e}")
            return {
                "error": 100,
                "description": "Internal error"
            }
    
    async def _handle_authenticate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle /authenticate callback - verify player session.
        
        Pragmatic calls this when a game loads to verify the player token.
        
        TODO: Implement with database lookup:
        1. Extract token/userId from payload
        2. Verify session exists and is valid
        3. Return player info and balance
        """
        # TODO: Implement - example response:
        # player = await db.users.find_one({"id": payload["userId"]})
        # return {
        #     "error": 0,
        #     "description": "Success",
        #     "userId": payload["userId"],
        #     "currency": "USD",
        #     "balance": int(player["wallet_balance"] * 100),  # Convert to cents
        #     "country": "US",
        #     "jurisdiction": "default"
        # }
        
        raise NotImplementedError("Pragmatic authenticate callback not implemented")
    
    async def _handle_balance(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle /balance callback - return current player balance.
        
        TODO: Implement with database lookup:
        1. Look up player by userId
        2. Return current balance
        """
        # TODO: Implement - example response:
        # player = await db.users.find_one({"id": payload["userId"]})
        # return {
        #     "error": 0,
        #     "description": "Success",
        #     "balance": int(player["wallet_balance"] * 100),
        #     "currency": "USD"
        # }
        
        raise NotImplementedError("Pragmatic balance callback not implemented")
    
    async def _handle_bet(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle /bet callback - deduct bet amount from player wallet.
        
        CRITICAL: This must be idempotent! Check if bet already processed
        using the 'reference' field before deducting balance.
        
        TODO: Implement with:
        1. Check idempotency (reference already processed?)
        2. Verify sufficient balance
        3. Deduct balance atomically
        4. Create transaction record
        5. Return new balance
        """
        # TODO: Implement - example response:
        # 
        # # Check idempotency
        # existing = await db.transactions.find_one({
        #     "metadata.provider_tx_id": payload["reference"],
        #     "provider_id": "pragmatic"
        # })
        # if existing:
        #     # Already processed - return current balance
        #     player = await db.users.find_one({"id": payload["userId"]})
        #     return {
        #         "error": 0,
        #         "balance": int(player["wallet_balance"] * 100),
        #         "currency": "USD"
        #     }
        # 
        # # Get player and check balance
        # amount_cents = int(payload["amount"])
        # amount = amount_cents / 100.0  # Convert from cents
        # 
        # player = await db.users.find_one({"id": payload["userId"]})
        # if player["wallet_balance"] < amount:
        #     return {
        #         "error": 1,
        #         "description": "Insufficient funds"
        #     }
        # 
        # # Deduct balance and record transaction
        # new_balance = player["wallet_balance"] - amount
        # await db.users.update_one(
        #     {"id": payload["userId"]},
        #     {"$set": {"wallet_balance": new_balance}}
        # )
        # 
        # # Create transaction record
        # tx = Transaction(
        #     tenant_id=player["tenant_id"],
        #     player_id=payload["userId"],
        #     game_id=payload["gameId"],
        #     provider_id="pragmatic",
        #     round_id=payload["roundId"],
        #     type="bet",
        #     amount=amount,
        #     balance_before=player["wallet_balance"],
        #     balance_after=new_balance,
        #     metadata={"provider_tx_id": payload["reference"]}
        # )
        # await db.transactions.insert_one(tx.model_dump())
        # 
        # return {
        #     "error": 0,
        #     "description": "Success",
        #     "balance": int(new_balance * 100),
        #     "currency": "USD"
        # }
        
        raise NotImplementedError("Pragmatic bet callback not implemented")
    
    async def _handle_result(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle /result callback - credit win amount to player wallet.
        
        CRITICAL: This must be idempotent! Check if result already processed.
        
        TODO: Implement similar to _handle_bet but crediting instead of debiting.
        """
        raise NotImplementedError("Pragmatic result callback not implemented")
    
    async def _handle_refund(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle /refund callback - rollback a previous bet.
        
        CRITICAL: 
        - Must be idempotent
        - If original bet not found, return success (Pragmatic may have already refunded)
        - Only refund if bet wasn't already settled with a win
        
        TODO: Implement with:
        1. Find original bet by reference
        2. If not found or already refunded, return success
        3. Credit bet amount back
        4. Create rollback transaction
        """
        raise NotImplementedError("Pragmatic refund callback not implemented")
    
    # =========================================================================
    # SESSION VALIDATION
    # =========================================================================
    
    async def validate_session(self, session_id: str) -> bool:
        """
        Validate if a session is still active.
        
        For Pragmatic, sessions are validated on their end.
        We primarily track sessions for internal auditing.
        """
        if not self._configured:
            return False
        
        # TODO: Implement session lookup
        # Our sessions are stored in game_sessions collection
        # session = await db.game_sessions.find_one({"id": session_id})
        # return session and session["status"] == "active"
        
        raise NotImplementedError("Pragmatic session validation not implemented")
    
    async def close_session(self, session_id: str) -> bool:
        """
        Close/terminate a game session.
        
        For Pragmatic, sessions close automatically when the game window closes.
        This method updates our internal tracking.
        """
        if not self._configured:
            return False
        
        # TODO: Update our session record
        # await db.game_sessions.update_one(
        #     {"id": session_id},
        #     {"$set": {"status": "closed", "closed_at": datetime.now(timezone.utc)}}
        # )
        # return True
        
        raise NotImplementedError("Pragmatic session close not implemented")
    
    # =========================================================================
    # GAME CATALOG
    # =========================================================================
    
    async def get_game_list(self) -> list:
        """
        Fetch available games from Pragmatic Play.
        
        This should be called periodically to sync the game catalog.
        Games are stored in our database with provider_id = "pragmatic".
        
        TODO: Implement API call to get game list
        """
        if not self._configured:
            return []
        
        # TODO: Implement API call
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(
        #         f"{self.api_url}/IntegrationService/v3/http/CasinoGameAPI/getCasinoGames",
        #         data={"casinoId": self.casino_id, ...},
        #         timeout=30.0
        #     )
        #     games = response.json().get("gameList", [])
        #     return games
        
        raise NotImplementedError("Pragmatic game list not implemented")
