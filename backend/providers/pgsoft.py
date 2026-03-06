"""
PGSoft Provider Adapter

This adapter implements the Seamless Wallet integration pattern for PGSoft.

INTEGRATION REQUIREMENTS:
- Valid PGSoft commercial contract
- API credentials from PGSoft operator portal
- Registered callback URLs with PGSoft

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


class PGSoftAdapter(GameProviderAdapter):
    """
    PGSoft Seamless Wallet adapter.
    
    Required environment variables:
    - PGSOFT_API_URL: API endpoint for game launch
    - PGSOFT_OPERATOR_TOKEN: Operator authentication token
    - PGSOFT_SECRET_KEY: Shared key for callback signature verification
    
    PGSoft uses a unified callback endpoint with an 'action' parameter
    to distinguish between different operation types.
    """
    
    def __init__(self):
        self.api_url = os.environ.get('PGSOFT_API_URL', '')
        self.operator_token = os.environ.get('PGSOFT_OPERATOR_TOKEN', '')
        self.secret_key = os.environ.get('PGSOFT_SECRET_KEY', '')
        self._configured = bool(self.api_url and self.operator_token and self.secret_key)
        
        if self._configured:
            logger.info("PGSoft adapter initialized with credentials")
        else:
            logger.warning("PGSoft adapter not configured - missing credentials")
    
    @property
    def provider_id(self) -> str:
        return "pgsoft"
    
    @property
    def provider_name(self) -> str:
        return "PGSoft"
    
    @property
    def is_configured(self) -> bool:
        """Check if provider credentials are configured"""
        return self._configured
    
    # =========================================================================
    # SIGNATURE METHODS
    # =========================================================================
    
    def generate_signature(self, params: Dict[str, Any]) -> str:
        """
        Generate SHA256 signature for API requests.
        
        PGSoft typically uses sorted parameter concatenation for signing.
        
        TODO: Confirm exact signature method with PGSoft documentation.
        """
        # Remove signature from params if present
        params_copy = {k: v for k, v in params.items() if k != 'signature'}
        
        # Sort and concatenate
        sorted_params = '&'.join(
            f"{k}={v}" for k, v in sorted(params_copy.items())
        )
        
        return hmac.new(
            self.secret_key.encode('utf-8'),
            sorted_params.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def verify_callback_signature(self, params: Dict[str, Any], received_signature: str) -> bool:
        """
        Verify signature from PGSoft callback.
        
        Args:
            params: Callback parameters (without signature)
            received_signature: Signature value from callback
            
        Returns:
            True if signature is valid
        """
        expected_signature = self.generate_signature(params)
        return hmac.compare_digest(expected_signature, received_signature)
    
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
        Create a game session with PGSoft.
        
        PGSoft's game launch typically returns a direct game URL.
        The session is established when the player opens the game
        and PGSoft calls our VerifySession callback.
        
        Args:
            player_id: Our internal player ID
            game_id: PGSoft game code
            tenant_id: Tenant identifier
            currency: Player's currency
            language: UI language
            
        Returns:
            {
                "session_id": str,      # Our session token
                "launch_url": str,      # URL to open game
                "expires_at": datetime  # Session expiry
            }
        """
        if not self._configured:
            raise NotImplementedError(
                "PGSoft adapter not configured. "
                "Set PGSOFT_API_URL, PGSOFT_OPERATOR_TOKEN, and PGSOFT_SECRET_KEY "
                "in backend/.env"
            )
        
        # Generate our session token
        import uuid
        session_token = f"pgs_{tenant_id}_{player_id}_{uuid.uuid4().hex[:12]}"
        
        # TODO: Implement actual API call to PGSoft
        # =====================================================================
        # EXAMPLE IMPLEMENTATION (not production-ready):
        #
        # request_data = {
        #     "operator_token": self.operator_token,
        #     "player_name": player_id,
        #     "game_code": game_id,
        #     "currency": currency,
        #     "language": language,
        #     "operator_player_session": session_token,
        #     "ip": kwargs.get("ip", "0.0.0.0"),
        #     "bet_type": kwargs.get("bet_type", 1),  # 1 = real money
        # }
        # request_data["signature"] = self.generate_signature(request_data)
        #
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(
        #         f"{self.api_url}/game/v2/Launch",
        #         data=request_data,  # PGSoft uses form-encoded
        #         timeout=10.0
        #     )
        #     
        #     if response.status_code != 200:
        #         logger.error(f"PGSoft API error: {response.text}")
        #         raise Exception("Failed to create game session")
        #     
        #     data = response.json()
        #     
        #     if data.get("error"):
        #         raise Exception(f"PGSoft error: {data['error']['message']}")
        #     
        #     return {
        #         "session_id": session_token,
        #         "launch_url": data["data"]["game_url"],
        #         "expires_at": datetime.now(timezone.utc) + timedelta(hours=2)
        #     }
        # =====================================================================
        
        raise NotImplementedError(
            "PGSoft create_session not yet implemented. "
            "See /docs/PROVIDERS.md for integration guide."
        )
    
    async def get_launch_url(self, session_id: str) -> str:
        """
        Get launch URL for an existing session.
        
        PGSoft sessions are typically single-use.
        """
        if not self._configured:
            raise NotImplementedError("PGSoft adapter not configured")
        
        raise NotImplementedError(
            "PGSoft get_launch_url not implemented. "
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
        Handle PGSoft callbacks.
        
        PGSoft uses a unified callback endpoint with different 'action' values:
        - VerifySession: Authenticate player session
        - GetBalance: Return current balance
        - Bet: Deduct bet amount
        - Settle: Credit win amount
        - Cancel: Rollback transaction
        - Bonus: Apply bonus credit
        
        Args:
            action: Action type from callback
            payload: Callback data (form-encoded, converted to dict)
            
        Returns:
            Response dict in PGSoft's expected format:
            {
                "data": {
                    "player_name": "...",
                    "currency": "USD",
                    "balance_amount": "1000.00",
                    "updated_time": "..."
                },
                "error": null  # or {"code": "...", "message": "..."}
            }
        """
        if not self._configured:
            return self._error_response("PROVIDER_NOT_CONFIGURED", "Provider not configured")
        
        # Verify signature before processing
        received_signature = payload.pop("signature", "")
        if received_signature and not self.verify_callback_signature(payload, received_signature):
            logger.warning(f"Invalid signature in PGSoft {action} callback")
            return self._error_response("INVALID_SIGNATURE", "Signature verification failed")
        
        # Verify operator token
        if payload.get("operator_token") != self.operator_token:
            logger.warning("Invalid operator token in PGSoft callback")
            return self._error_response("INVALID_OPERATOR", "Invalid operator token")
        
        # Route to specific handler
        handlers = {
            "VerifySession": self._handle_verify_session,
            "GetBalance": self._handle_get_balance,
            "Bet": self._handle_bet,
            "Settle": self._handle_settle,
            "Cancel": self._handle_cancel,
            "Bonus": self._handle_bonus,
        }
        
        handler = handlers.get(action)
        if not handler:
            logger.error(f"Unknown PGSoft callback action: {action}")
            return self._error_response("UNKNOWN_ACTION", f"Unknown action: {action}")
        
        try:
            return await handler(payload)
        except Exception as e:
            logger.exception(f"Error handling PGSoft {action} callback: {e}")
            return self._error_response("INTERNAL_ERROR", "Internal server error")
    
    def _success_response(
        self,
        player_name: str,
        currency: str,
        balance: float,
        **extra
    ) -> Dict[str, Any]:
        """Build successful response in PGSoft format"""
        response_data = {
            "player_name": player_name,
            "currency": currency,
            "balance_amount": f"{balance:.2f}",
            "updated_time": datetime.now(timezone.utc).isoformat()
        }
        response_data.update(extra)
        
        return {
            "data": response_data,
            "error": None
        }
    
    def _error_response(self, code: str, message: str) -> Dict[str, Any]:
        """Build error response in PGSoft format"""
        return {
            "data": None,
            "error": {
                "code": code,
                "message": message
            }
        }
    
    async def _handle_verify_session(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle VerifySession callback - authenticate player.
        
        PGSoft calls this when a game loads to verify the player session token.
        
        Expected payload:
        - trace_id: Request tracking ID
        - operator_token: Our operator token
        - secret_key: Shared secret (for verification)
        - operator_player_session: Session token we generated during launch
        - bet_type: Game mode (1 = real money, 0 = demo)
        - ip: Player's IP address
        
        TODO: Implement with database lookup:
        1. Verify operator_player_session exists
        2. Return player info and balance
        """
        # TODO: Implement - example:
        # session_token = payload.get("operator_player_session")
        # session = await db.game_sessions.find_one({"id": session_token})
        # 
        # if not session:
        #     return self._error_response("INVALID_SESSION", "Session not found")
        # 
        # player = await db.users.find_one({"id": session["player_id"]})
        # 
        # return self._success_response(
        #     player_name=player["id"],
        #     currency="USD",
        #     balance=player["wallet_balance"],
        #     nickname=player["display_name"]
        # )
        
        raise NotImplementedError("PGSoft VerifySession callback not implemented")
    
    async def _handle_get_balance(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle GetBalance callback - return current player balance.
        
        Expected payload:
        - trace_id: Request tracking ID
        - player_name: Our player ID
        - currency: Expected currency
        
        TODO: Implement with database lookup
        """
        # TODO: Implement - example:
        # player_name = payload.get("player_name")
        # player = await db.users.find_one({"id": player_name})
        # 
        # if not player:
        #     return self._error_response("PLAYER_NOT_FOUND", "Player not found")
        # 
        # return self._success_response(
        #     player_name=player_name,
        #     currency=payload.get("currency", "USD"),
        #     balance=player["wallet_balance"]
        # )
        
        raise NotImplementedError("PGSoft GetBalance callback not implemented")
    
    async def _handle_bet(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle Bet callback - deduct bet amount from player wallet.
        
        CRITICAL: Must be idempotent using bet_id/transaction_id.
        
        Expected payload:
        - trace_id: Request tracking ID
        - player_name: Our player ID
        - currency: Currency
        - bet_id: PGSoft's bet/round identifier
        - transaction_id: Unique transaction ID (use for idempotency)
        - bet_amount: Amount to deduct
        
        TODO: Implement with:
        1. Check idempotency (transaction_id already processed?)
        2. Verify sufficient balance
        3. Deduct balance atomically
        4. Create transaction record
        5. Return new balance
        """
        # TODO: Implement - example:
        # player_name = payload.get("player_name")
        # transaction_id = payload.get("transaction_id")
        # bet_amount = float(payload.get("bet_amount", 0))
        # 
        # # Check idempotency
        # existing = await db.transactions.find_one({
        #     "metadata.provider_tx_id": transaction_id,
        #     "provider_id": "pgsoft"
        # })
        # if existing:
        #     player = await db.users.find_one({"id": player_name})
        #     return self._success_response(
        #         player_name=player_name,
        #         currency=payload.get("currency", "USD"),
        #         balance=player["wallet_balance"]
        #     )
        # 
        # # Check balance
        # player = await db.users.find_one({"id": player_name})
        # if player["wallet_balance"] < bet_amount:
        #     return self._error_response("INSUFFICIENT_FUNDS", "Insufficient balance")
        # 
        # # Deduct and record
        # new_balance = player["wallet_balance"] - bet_amount
        # await db.users.update_one(
        #     {"id": player_name},
        #     {"$set": {"wallet_balance": new_balance}}
        # )
        # 
        # tx = Transaction(
        #     tenant_id=player["tenant_id"],
        #     player_id=player_name,
        #     provider_id="pgsoft",
        #     round_id=payload.get("bet_id"),
        #     type="bet",
        #     amount=bet_amount,
        #     balance_before=player["wallet_balance"],
        #     balance_after=new_balance,
        #     metadata={"provider_tx_id": transaction_id}
        # )
        # await db.transactions.insert_one(tx.model_dump())
        # 
        # return self._success_response(
        #     player_name=player_name,
        #     currency=payload.get("currency", "USD"),
        #     balance=new_balance
        # )
        
        raise NotImplementedError("PGSoft Bet callback not implemented")
    
    async def _handle_settle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle Settle callback - credit win amount to player wallet.
        
        CRITICAL: Must be idempotent using transaction_id.
        
        Expected payload:
        - trace_id: Request tracking ID
        - player_name: Our player ID
        - currency: Currency
        - bet_id: Original bet's ID
        - transaction_id: Unique transaction ID for this settle
        - win_amount: Amount to credit (0 if loss)
        
        TODO: Implement similar to _handle_bet but crediting.
        """
        raise NotImplementedError("PGSoft Settle callback not implemented")
    
    async def _handle_cancel(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle Cancel callback - rollback a previous bet.
        
        CRITICAL:
        - Must be idempotent
        - If original bet not found, return success
        - Only cancel if bet wasn't already settled
        
        Expected payload:
        - trace_id: Request tracking ID
        - player_name: Our player ID
        - parent_bet_id: Original bet to cancel
        - transaction_id: Cancel transaction ID
        
        TODO: Implement with:
        1. Find original bet by parent_bet_id
        2. If not found or already cancelled, return current balance
        3. Credit bet amount back
        4. Create rollback transaction
        """
        raise NotImplementedError("PGSoft Cancel callback not implemented")
    
    async def _handle_bonus(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle Bonus callback - apply bonus credit.
        
        Expected payload:
        - trace_id: Request tracking ID
        - player_name: Our player ID
        - transaction_id: Bonus transaction ID
        - bonus_amount: Amount to credit
        
        TODO: Implement bonus crediting with proper tracking.
        """
        raise NotImplementedError("PGSoft Bonus callback not implemented")
    
    # =========================================================================
    # SESSION VALIDATION
    # =========================================================================
    
    async def validate_session(self, session_id: str) -> bool:
        """
        Validate if a session is still active.
        
        PGSoft sessions are validated via the VerifySession callback.
        This method checks our internal session record.
        """
        if not self._configured:
            return False
        
        # TODO: Implement session lookup
        # session = await db.game_sessions.find_one({"id": session_id})
        # return session and session["status"] == "active"
        
        raise NotImplementedError("PGSoft session validation not implemented")
    
    async def close_session(self, session_id: str) -> bool:
        """
        Close/terminate a game session.
        
        PGSoft sessions typically expire automatically.
        This updates our internal tracking.
        """
        if not self._configured:
            return False
        
        # TODO: Update our session record
        # await db.game_sessions.update_one(
        #     {"id": session_id},
        #     {"$set": {"status": "closed", "closed_at": datetime.now(timezone.utc)}}
        # )
        # return True
        
        raise NotImplementedError("PGSoft session close not implemented")
    
    # =========================================================================
    # GAME CATALOG
    # =========================================================================
    
    async def get_game_list(self) -> list:
        """
        Fetch available games from PGSoft.
        
        PGSoft provides game lists through their operator portal or API.
        Games should be synced periodically.
        
        TODO: Implement API call if PGSoft provides it,
        or manual import from their portal.
        """
        if not self._configured:
            return []
        
        raise NotImplementedError("PGSoft game list not implemented")
