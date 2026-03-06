"""VD7 Aggregator - Callback Handlers.

Handles inbound callbacks from VD7:
- getBalance: Return player balance
- debit: Process bet (deduct balance)
- credit: Process win (add balance)
- cancelBet: Cancel bet (refund bet - deduct win)
- gameReward: Process bonus/reward
- postBetHistory: Combined debit+credit

All handlers use existing wallet/ledger.py for atomic operations.
"""

from __future__ import annotations

import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============ REQUEST MODELS ============

class VD7BaseRequest(BaseModel):
    """Base fields for all VD7 callbacks."""
    username: str
    agent_code: str
    currency_code: str
    action_id: str
    sign: str
    provider_code: Optional[str] = None
    game_token: Optional[str] = None
    session_game_token: Optional[str] = None


class VD7GetBalanceRequest(VD7BaseRequest):
    """GetBalance request - NO transaction_id."""
    pass


class VD7DebitRequest(VD7BaseRequest):
    """Debit (bet) request."""
    amount: float
    transaction_id: str
    round_id: str
    type: str = "placebet"
    gamecode: Optional[str] = None
    bet_time: Optional[int] = None


class VD7CreditRequest(VD7BaseRequest):
    """Credit (win) request."""
    amount: float
    transaction_id: str
    round_id: str
    type: str = "win"
    gamecode: Optional[str] = None
    valid_bet_amount: Optional[float] = None
    settle_time: Optional[int] = None


class VD7CancelBetRequest(VD7BaseRequest):
    """CancelBet request.
    
    Formula: Balance after = Balance before + betAmount - winLoseAmount
    Balance cannot go negative.
    """
    bet_amount: float
    win_amount: float = 0
    transaction_id: str
    round_id: str
    type: str = "cancelbet"
    gamecode: Optional[str] = None


class VD7GameRewardTransaction(BaseModel):
    """Single transaction in gameReward."""
    amount: float
    transaction_id: str
    round_id: str
    game_token: Optional[str] = None
    reward_time: Optional[str] = None


class VD7GameRewardRequest(VD7BaseRequest):
    """GameReward request - NO transaction_id in sign."""
    gamecode: Optional[str] = None
    type: str = "reward"
    transactions: list[VD7GameRewardTransaction] = Field(default_factory=list)


class VD7PostBetHistoryRequest(VD7BaseRequest):
    """PostBetHistory - combined debit+credit in single call."""
    bet_amount: float
    win_amount: float
    transaction_id: str
    round_id: str
    type: str = "postbet"
    gamecode: Optional[str] = None
    valid_bet_amount: Optional[float] = None
    is_free_spin: bool = False
    reference_id: Optional[str] = None
    remaining_free_spin: int = 0


# ============ RESPONSE HELPERS ============

def vd7_success(
    balance: float,
    currency_code: str,
    session_game_token: Optional[str] = None,
    extra: Optional[dict] = None,
) -> dict:
    """Generate VD7 success response."""
    response = {
        "code": 0,
        "msg": "success",
        "balance": balance,
        "currency_code": currency_code,
    }
    if session_game_token:
        response["session_game_token"] = session_game_token
    if extra:
        response.update(extra)
    return response


def vd7_error(code: int, msg: str, balance: float = 0, currency_code: str = "IDR") -> dict:
    """Generate VD7 error response."""
    return {
        "code": code,
        "msg": msg,
        "balance": balance,
        "currency_code": currency_code,
    }


# ============ VD7 ERROR CODES ============

class VD7ErrorCodes:
    """VD7 standard error codes."""
    SUCCESS = 0
    INVALID_BEARER_TOKEN = 101
    INVALID_PLAYER = 102
    VALIDATION_ERROR = 103
    INVALID_IP = 104
    BRAND_DISABLED = 105
    INVALID_GAME = 106
    REQUEST_TIMEOUT = 108
    PROVIDER_DISABLED = 301
    PROVIDER_NOT_FOUND = 302
    GAME_INVALID_ARGS = 303
    DUPLICATE_TRANSACTION = 304
    PROVIDER_ERROR = 305
    INVALID_PLATFORM = 306
    WALLET_TYPE_NOT_SUPPORTED = 307
    INVALID_CURRENCY = 308
    GAME_DISABLED = 345
    GAME_MAINTENANCE = 346
    INSUFFICIENT_BALANCE = 351
    PLAYER_DISABLED = 353
    PLAYER_NOT_FOUND = 354
    BET_LIMIT_REACHED = 356
    CURRENCY_NOT_SUPPORTED = 358
    TRANSACTION_ERROR = 360
    FUNCTION_NOT_SUPPORTED = 361
    TRIGGER_CANCEL = 365
    TRANSACTION_PENDING = 366
    TIMEOUT_ERROR = 998
    UNKNOWN_ERROR = 999


# ============ CALLBACK HANDLER CLASS ============

class VD7CallbackHandler:
    """
    Handles VD7 callback operations.
    
    Requires:
    - db: MongoDB database connection
    - tenant_id: Resolved tenant ID
    - agent_secret: For signature verification
    """
    
    def __init__(self, db, tenant_id: str, agent_code: str, agent_secret: str):
        self.db = db
        self.tenant_id = tenant_id
        self.agent_code = agent_code
        self.agent_secret = agent_secret
    
    def _to_decimal(self, value: float, currency: str) -> Decimal:
        """Convert float to Decimal with proper precision."""
        quant = Decimal("1") if currency.upper() == "IDR" else Decimal("0.01")
        return Decimal(str(value)).quantize(quant, rounding=ROUND_HALF_UP)
    
    def _to_display(self, value: Decimal, currency: str) -> float | int:
        """Convert Decimal to display value."""
        if currency.upper() == "IDR":
            return int(value)
        return float(value)
    
    async def _get_player(self, username: str) -> Optional[dict]:
        """Get player by username (which is player_id).
        
        username in VD7 = player_id in LooxGame
        """
        return await self.db.users.find_one(
            {
                "id": username,
                "tenant_id": self.tenant_id,
                "role": "player",
                "is_active": True,
            },
            {"_id": 0}
        )
    
    async def _find_tx(self, transaction_id: str, player_id: str) -> Optional[dict]:
        """Find existing transaction for idempotency."""
        return await self.db.transactions.find_one(
            {
                "tenant_id": self.tenant_id,
                "player_id": player_id,
                "tx_id": transaction_id,
            },
            {"_id": 0}
        )
    
    async def handle_get_balance(self, req: VD7GetBalanceRequest) -> dict:
        """Handle GetBalance callback."""
        player = await self._get_player(req.username)
        if not player:
            return vd7_error(
                VD7ErrorCodes.PLAYER_NOT_FOUND,
                "Player not found",
                currency_code=req.currency_code
            )
        
        balance = self._to_display(
            self._to_decimal(player.get("wallet_balance", 0), req.currency_code),
            req.currency_code
        )
        
        return vd7_success(
            balance=balance,
            currency_code=req.currency_code,
            session_game_token=req.session_game_token,
            extra={
                "agent_code": self.agent_code,
                "provider_code": req.provider_code,
            }
        )
    
    async def handle_debit(self, req: VD7DebitRequest) -> dict:
        """Handle Debit (bet) callback."""
        from wallet import ledger as wallet_ledger
        
        player = await self._get_player(req.username)
        if not player:
            return vd7_error(
                VD7ErrorCodes.PLAYER_NOT_FOUND,
                "Player not found",
                currency_code=req.currency_code
            )
        
        # Idempotency check
        existing_tx = await self._find_tx(req.transaction_id, req.username)
        if existing_tx:
            return vd7_success(
                balance=existing_tx.get("balance_after", 0),
                currency_code=req.currency_code,
                session_game_token=req.session_game_token,
            )
        
        currency = req.currency_code
        amount = wallet_ledger.money_to_decimal(req.amount, currency)
        current_balance = wallet_ledger.money_to_decimal(player.get("wallet_balance", 0), currency)
        
        # Check sufficient balance
        if current_balance < amount:
            return vd7_error(
                VD7ErrorCodes.INSUFFICIENT_BALANCE,
                "Insufficient balance",
                balance=wallet_ledger.decimal_to_amount(current_balance, currency),
                currency_code=currency
            )
        
        # Atomic debit
        new_balance = await wallet_ledger.atomic_debit(
            self.db,
            tenant_id=self.tenant_id,
            player_id=req.username,
            amount=amount,
            currency=currency
        )
        
        if new_balance is None:
            return vd7_error(
                VD7ErrorCodes.TRANSACTION_ERROR,
                "Debit failed - concurrent conflict",
                balance=wallet_ledger.decimal_to_amount(current_balance, currency),
                currency_code=currency
            )
        
        # Record transaction
        balance_before = new_balance + amount
        await wallet_ledger.record_tx(
            self.db,
            tenant_id=self.tenant_id,
            player_id=req.username,
            tx_id=req.transaction_id,
            tx_type="bet",
            amount=amount,
            currency=currency,
            balance_before=balance_before,
            balance_after=new_balance,
            session_id=req.session_game_token,
            round_id=req.round_id,
            description="VD7 debit",
            metadata={
                "source": "vd7",
                "operation": "debit",
                "provider_code": req.provider_code,
                "gamecode": req.gamecode,
                "action_id": req.action_id,
                "bet_time": req.bet_time,
            }
        )
        
        return vd7_success(
            balance=wallet_ledger.decimal_to_amount(new_balance, currency),
            currency_code=currency,
            session_game_token=req.session_game_token,
        )
    
    async def handle_credit(self, req: VD7CreditRequest) -> dict:
        """Handle Credit (win) callback."""
        from wallet import ledger as wallet_ledger
        
        player = await self._get_player(req.username)
        if not player:
            return vd7_error(
                VD7ErrorCodes.PLAYER_NOT_FOUND,
                "Player not found",
                currency_code=req.currency_code
            )
        
        # Idempotency check
        existing_tx = await self._find_tx(req.transaction_id, req.username)
        if existing_tx:
            return vd7_success(
                balance=existing_tx.get("balance_after", 0),
                currency_code=req.currency_code,
                session_game_token=req.session_game_token,
            )
        
        currency = req.currency_code
        amount = wallet_ledger.money_to_decimal(req.amount, currency)
        
        # Atomic credit
        new_balance = await wallet_ledger.atomic_credit(
            self.db,
            tenant_id=self.tenant_id,
            player_id=req.username,
            amount=amount,
            currency=currency
        )
        
        if new_balance is None:
            current = wallet_ledger.money_to_decimal(player.get("wallet_balance", 0), currency)
            return vd7_error(
                VD7ErrorCodes.TRANSACTION_ERROR,
                "Credit failed - player not found or inactive",
                balance=wallet_ledger.decimal_to_amount(current, currency),
                currency_code=currency
            )
        
        # Record transaction
        balance_before = new_balance - amount
        await wallet_ledger.record_tx(
            self.db,
            tenant_id=self.tenant_id,
            player_id=req.username,
            tx_id=req.transaction_id,
            tx_type="win",
            amount=amount,
            currency=currency,
            balance_before=balance_before,
            balance_after=new_balance,
            session_id=req.session_game_token,
            round_id=req.round_id,
            description="VD7 credit",
            metadata={
                "source": "vd7",
                "operation": "credit",
                "provider_code": req.provider_code,
                "gamecode": req.gamecode,
                "action_id": req.action_id,
                "valid_bet_amount": req.valid_bet_amount,
                "settle_time": req.settle_time,
            }
        )
        
        return vd7_success(
            balance=wallet_ledger.decimal_to_amount(new_balance, currency),
            currency_code=currency,
            session_game_token=req.session_game_token,
        )
    
    async def handle_cancel_bet(self, req: VD7CancelBetRequest) -> dict:
        """Handle CancelBet callback.
        
        Formula: Balance after = Balance before + betAmount - winLoseAmount
        Balance cannot go negative.
        """
        from wallet import ledger as wallet_ledger
        
        player = await self._get_player(req.username)
        if not player:
            return vd7_error(
                VD7ErrorCodes.PLAYER_NOT_FOUND,
                "Player not found",
                currency_code=req.currency_code
            )
        
        # Idempotency check
        existing_tx = await self._find_tx(req.transaction_id, req.username)
        if existing_tx:
            return vd7_success(
                balance=existing_tx.get("balance_after", 0),
                currency_code=req.currency_code,
                session_game_token=req.session_game_token,
            )
        
        currency = req.currency_code
        bet_amount = wallet_ledger.money_to_decimal(req.bet_amount, currency)
        win_amount = wallet_ledger.money_to_decimal(req.win_amount, currency)
        current_balance = wallet_ledger.money_to_decimal(player.get("wallet_balance", 0), currency)
        
        # Calculate net change: +betAmount (refund) -winAmount (deduct prior win)
        net_change = bet_amount - win_amount
        projected_balance = current_balance + net_change
        
        # Balance cannot be negative
        if projected_balance < 0:
            return vd7_error(
                VD7ErrorCodes.INSUFFICIENT_BALANCE,
                "Insufficient balance for cancel (would go negative)",
                balance=wallet_ledger.decimal_to_amount(current_balance, currency),
                currency_code=currency
            )
        
        # Atomic update with balance check
        if net_change >= 0:
            # Net positive: credit operation
            new_balance = await wallet_ledger.atomic_credit(
                self.db,
                tenant_id=self.tenant_id,
                player_id=req.username,
                amount=abs(net_change),
                currency=currency
            )
        else:
            # Net negative: debit operation (need balance check)
            new_balance = await wallet_ledger.atomic_debit(
                self.db,
                tenant_id=self.tenant_id,
                player_id=req.username,
                amount=abs(net_change),
                currency=currency
            )
        
        if new_balance is None:
            return vd7_error(
                VD7ErrorCodes.TRANSACTION_ERROR,
                "CancelBet failed - concurrent conflict or insufficient balance",
                balance=wallet_ledger.decimal_to_amount(current_balance, currency),
                currency_code=currency
            )
        
        # Record transaction
        await wallet_ledger.record_tx(
            self.db,
            tenant_id=self.tenant_id,
            player_id=req.username,
            tx_id=req.transaction_id,
            tx_type="cancelbet",
            amount=abs(net_change),
            currency=currency,
            balance_before=current_balance,
            balance_after=new_balance,
            session_id=req.session_game_token,
            round_id=req.round_id,
            description="VD7 cancelbet",
            metadata={
                "source": "vd7",
                "operation": "cancelbet",
                "provider_code": req.provider_code,
                "gamecode": req.gamecode,
                "action_id": req.action_id,
                "bet_amount": float(bet_amount),
                "win_amount": float(win_amount),
                "net_change": float(net_change),
            }
        )
        
        return vd7_success(
            balance=wallet_ledger.decimal_to_amount(new_balance, currency),
            currency_code=currency,
            session_game_token=req.session_game_token,
        )
    
    async def handle_game_reward(self, req: VD7GameRewardRequest) -> dict:
        """Handle GameReward callback (bonuses/rewards)."""
        from wallet import ledger as wallet_ledger
        
        player = await self._get_player(req.username)
        if not player:
            return vd7_error(
                VD7ErrorCodes.PLAYER_NOT_FOUND,
                "Player not found",
                currency_code=req.currency_code
            )
        
        currency = req.currency_code
        total_reward = Decimal("0")
        processed_txs = []
        
        for tx in req.transactions:
            # Idempotency check per transaction
            existing = await self._find_tx(tx.transaction_id, req.username)
            if existing:
                processed_txs.append({
                    "transaction_id": tx.transaction_id,
                    "status": "duplicate",
                    "balance_after": existing.get("balance_after", 0),
                })
                continue
            
            amount = wallet_ledger.money_to_decimal(tx.amount, currency)
            total_reward += amount
            
            # Atomic credit for reward
            new_balance = await wallet_ledger.atomic_credit(
                self.db,
                tenant_id=self.tenant_id,
                player_id=req.username,
                amount=amount,
                currency=currency
            )
            
            if new_balance is None:
                processed_txs.append({
                    "transaction_id": tx.transaction_id,
                    "status": "failed",
                })
                continue
            
            balance_before = new_balance - amount
            await wallet_ledger.record_tx(
                self.db,
                tenant_id=self.tenant_id,
                player_id=req.username,
                tx_id=tx.transaction_id,
                tx_type="reward",
                amount=amount,
                currency=currency,
                balance_before=balance_before,
                balance_after=new_balance,
                session_id=tx.game_token,
                round_id=tx.round_id,
                description="VD7 reward",
                metadata={
                    "source": "vd7",
                    "operation": "gamereward",
                    "provider_code": req.provider_code,
                    "gamecode": req.gamecode,
                    "action_id": req.action_id,
                    "reward_time": tx.reward_time,
                }
            )
            
            processed_txs.append({
                "transaction_id": tx.transaction_id,
                "status": "success",
                "balance_after": wallet_ledger.decimal_to_amount(new_balance, currency),
            })
        
        # Get final balance
        player_updated = await self._get_player(req.username)
        final_balance = wallet_ledger.money_to_decimal(
            player_updated.get("wallet_balance", 0) if player_updated else 0,
            currency
        )
        
        return vd7_success(
            balance=wallet_ledger.decimal_to_amount(final_balance, currency),
            currency_code=currency,
            session_game_token=req.session_game_token,
            extra={"transactions": processed_txs}
        )
    
    async def handle_post_bet_history(self, req: VD7PostBetHistoryRequest) -> dict:
        """Handle PostBetHistory - combined debit+credit.
        
        Used by providers like Jili that send bet+win in single call.
        Net result = -bet_amount + win_amount
        """
        from wallet import ledger as wallet_ledger
        
        player = await self._get_player(req.username)
        if not player:
            return vd7_error(
                VD7ErrorCodes.PLAYER_NOT_FOUND,
                "Player not found",
                currency_code=req.currency_code
            )
        
        # Idempotency check
        existing_tx = await self._find_tx(req.transaction_id, req.username)
        if existing_tx:
            return vd7_success(
                balance=existing_tx.get("balance_after", 0),
                currency_code=req.currency_code,
                session_game_token=req.session_game_token,
            )
        
        currency = req.currency_code
        bet_amount = wallet_ledger.money_to_decimal(req.bet_amount, currency)
        win_amount = wallet_ledger.money_to_decimal(req.win_amount, currency)
        current_balance = wallet_ledger.money_to_decimal(player.get("wallet_balance", 0), currency)
        
        # Net change: -bet + win
        net_change = win_amount - bet_amount
        projected_balance = current_balance + net_change
        
        # Check if would go negative
        if projected_balance < 0:
            return vd7_error(
                VD7ErrorCodes.INSUFFICIENT_BALANCE,
                "Insufficient balance for bet",
                balance=wallet_ledger.decimal_to_amount(current_balance, currency),
                currency_code=currency
            )
        
        # Apply net change atomically
        if net_change >= 0:
            # Net win: credit
            if net_change > 0:
                new_balance = await wallet_ledger.atomic_credit(
                    self.db,
                    tenant_id=self.tenant_id,
                    player_id=req.username,
                    amount=net_change,
                    currency=currency
                )
            else:
                new_balance = current_balance  # No change
        else:
            # Net loss: debit
            new_balance = await wallet_ledger.atomic_debit(
                self.db,
                tenant_id=self.tenant_id,
                player_id=req.username,
                amount=abs(net_change),
                currency=currency
            )
        
        if new_balance is None:
            return vd7_error(
                VD7ErrorCodes.TRANSACTION_ERROR,
                "PostBetHistory failed - concurrent conflict or insufficient balance",
                balance=wallet_ledger.decimal_to_amount(current_balance, currency),
                currency_code=currency
            )
        
        # Record single combined transaction
        tx_type = "postbet_win" if net_change >= 0 else "postbet_loss"
        await wallet_ledger.record_tx(
            self.db,
            tenant_id=self.tenant_id,
            player_id=req.username,
            tx_id=req.transaction_id,
            tx_type=tx_type,
            amount=abs(net_change),
            currency=currency,
            balance_before=current_balance,
            balance_after=new_balance,
            session_id=req.session_game_token,
            round_id=req.round_id,
            description="VD7 postBetHistory",
            metadata={
                "source": "vd7",
                "operation": "postBetHistory",
                "provider_code": req.provider_code,
                "gamecode": req.gamecode,
                "action_id": req.action_id,
                "bet_amount": float(bet_amount),
                "win_amount": float(win_amount),
                "valid_bet_amount": req.valid_bet_amount,
                "is_free_spin": req.is_free_spin,
                "reference_id": req.reference_id,
                "remaining_free_spin": req.remaining_free_spin,
            }
        )
        
        return vd7_success(
            balance=wallet_ledger.decimal_to_amount(new_balance, currency),
            currency_code=currency,
            session_game_token=req.session_game_token,
        )
