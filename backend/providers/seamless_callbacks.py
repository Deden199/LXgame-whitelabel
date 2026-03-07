from __future__ import annotations

import secrets
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from wallet import ledger as wallet_ledger


class SeamlessUserBalanceRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    agent_code: str
    agent_secret: str
    user_code: str


class SeamlessGameSlotPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    provider_code: str
    game_code: str
    round_id: str
    is_round_finished: bool = False
    type: str = "BASE"
    bet: float = 0
    win: float = 0
    txn_id: str
    txn_type: str = "debit_credit"
    user_before_balance: Optional[float] = None
    user_after_balance: Optional[float] = None
    agent_before_balance: Optional[float] = None
    agent_after_balance: Optional[float] = None
    created_at: Optional[str] = None


class SeamlessGameCallbackRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    agent_code: str
    agent_secret: str
    agent_balance: Optional[float] = None
    user_code: str
    user_balance: Optional[float] = None
    user_total_credit: Optional[float] = None
    user_total_debit: Optional[float] = None
    game_type: str = "slot"
    slot: SeamlessGameSlotPayload


class SeamlessMoneyCallbackRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    agent_code: str
    agent_secret: str
    agent_type: Optional[str] = "Seamless"
    user_code: str
    provider_code: Optional[str] = None
    game_code: Optional[str] = None
    type: str
    agent_before_balance: Optional[float] = None
    agent_after_balance: Optional[float] = None
    user_before_balance: Optional[float] = None
    user_after_balance: Optional[float] = None
    amount: float = 0
    msg: Optional[str] = None
    created_at: Optional[str] = None


class SeamlessCallbackHandler:
    def __init__(self, db, tenant_id: str, agent_code: str, agent_secret: str, currency: str = "IDR"):
        self.db = db
        self.tenant_id = tenant_id
        self.agent_code = agent_code
        self.agent_secret = agent_secret
        self.currency = (currency or "PHP").upper()

    def authenticate(self, agent_code: str, agent_secret: str) -> bool:
        return secrets.compare_digest(agent_code or "", self.agent_code or "") and secrets.compare_digest(agent_secret or "", self.agent_secret or "")

    async def _get_player(self, user_code: str) -> Optional[dict[str, Any]]:
        return await self.db.users.find_one(
            {"id": user_code, "tenant_id": self.tenant_id, "role": "player", "is_active": True},
            {"_id": 0},
        )

    async def _get_existing_event(self, event_key: str) -> Optional[dict[str, Any]]:
        return await self.db.callback_events.find_one({"tenant_id": self.tenant_id, "event_key": event_key}, {"_id": 0})

    async def _record_event(self, event_key: str, callback_type: str, payload: dict[str, Any], response: dict[str, Any], idempotent: bool = False):
        await self.db.callback_events.update_one(
            {"tenant_id": self.tenant_id, "event_key": event_key},
            {
                "$set": {
                    "tenant_id": self.tenant_id,
                    "event_key": event_key,
                    "callback_type": callback_type,
                    "payload": payload,
                    "response": response,
                    "idempotent": idempotent,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                "$setOnInsert": {"created_at": datetime.now(timezone.utc).isoformat()},
            },
            upsert=True,
        )

    async def _success_balance(self, user_code: str) -> dict[str, Any]:
        player = await self._get_player(user_code)
        balance = player.get("wallet_balance", 0) if player else 0
        return {"status": 1, "user_balance": balance}

    async def handle_user_balance(self, req: SeamlessUserBalanceRequest) -> dict[str, Any]:
        player = await self._get_player(req.user_code)
        if not player:
            return {"status": 0, "user_balance": 0, "msg": "USER_NOT_FOUND"}
        return {"status": 1, "user_balance": player.get("wallet_balance", 0)}

    async def _record_transaction(
        self,
        *,
        tx_id: str,
        tx_type: str,
        player_id: str,
        amount: Decimal,
        balance_before: Decimal,
        balance_after: Decimal,
        round_id: Optional[str] = None,
        game_code: Optional[str] = None,
        provider_code: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ):
        await wallet_ledger.record_tx(
            self.db,
            tenant_id=self.tenant_id,
            player_id=player_id,
            tx_id=tx_id,
            tx_type=tx_type,
            amount=amount,
            currency=self.currency,
            balance_before=balance_before,
            balance_after=balance_after,
            round_id=round_id,
            description=f"Seamless {tx_type}",
            metadata={
                "source": "seamless_callback",
                "provider_code": provider_code,
                "game_code": game_code,
                **(metadata or {}),
            },
        )

    async def handle_game_callback(self, req: SeamlessGameCallbackRequest) -> dict[str, Any]:
        event_key = f"game_callback:{req.slot.txn_id}"
        existing = await self._get_existing_event(event_key)
        if existing:
            response = dict(existing.get("response") or {})
            response.setdefault("status", 1)
            response.setdefault("idempotent", True)
            return response

        player = await self._get_player(req.user_code)
        if not player:
            response = {"status": 0, "user_balance": 0, "msg": "USER_NOT_FOUND"}
            await self._record_event(event_key, "game_callback", req.model_dump(), response)
            return response

        current_balance = wallet_ledger.money_to_decimal(player.get("wallet_balance", 0), self.currency)
        bet_amount = wallet_ledger.money_to_decimal(req.slot.bet or 0, self.currency)
        win_amount = wallet_ledger.money_to_decimal(req.slot.win or 0, self.currency)
        txn_type = (req.slot.txn_type or "debit_credit").lower()
        after_bet = current_balance - bet_amount
        final_balance = after_bet + win_amount

        if txn_type in {"debit", "debit_credit"} and bet_amount > current_balance:
            response = {
                "status": 0,
                "user_balance": wallet_ledger.decimal_to_amount(current_balance, self.currency),
                "msg": "INSUFFICIENT_USER_FUNDS",
            }
            await self._record_event(event_key, "game_callback", req.model_dump(), response)
            return response

        net_change = win_amount - bet_amount
        new_balance: Optional[Decimal]
        if net_change < 0:
            new_balance = await wallet_ledger.atomic_debit(
                self.db,
                tenant_id=self.tenant_id,
                player_id=req.user_code,
                amount=abs(net_change),
                currency=self.currency,
            )
        elif net_change > 0:
            new_balance = await wallet_ledger.atomic_credit(
                self.db,
                tenant_id=self.tenant_id,
                player_id=req.user_code,
                amount=net_change,
                currency=self.currency,
            )
        else:
            new_balance = current_balance

        if new_balance is None:
            response = {
                "status": 0,
                "user_balance": wallet_ledger.decimal_to_amount(current_balance, self.currency),
                "msg": "TRANSACTION_FAILED",
            }
            await self._record_event(event_key, "game_callback", req.model_dump(), response)
            return response

        if bet_amount > 0:
            await self._record_transaction(
                tx_id=f"{req.slot.txn_id}:bet",
                tx_type="bet",
                player_id=req.user_code,
                amount=bet_amount,
                balance_before=current_balance,
                balance_after=after_bet,
                round_id=req.slot.round_id,
                game_code=req.slot.game_code,
                provider_code=req.slot.provider_code,
                metadata={"txn_type": txn_type, "event_txn_id": req.slot.txn_id},
            )
        if win_amount > 0:
            await self._record_transaction(
                tx_id=f"{req.slot.txn_id}:win",
                tx_type="win",
                player_id=req.user_code,
                amount=win_amount,
                balance_before=after_bet,
                balance_after=final_balance,
                round_id=req.slot.round_id,
                game_code=req.slot.game_code,
                provider_code=req.slot.provider_code,
                metadata={"txn_type": txn_type, "event_txn_id": req.slot.txn_id},
            )

        response = {"status": 1, "user_balance": wallet_ledger.decimal_to_amount(new_balance, self.currency)}
        await self._record_event(event_key, "game_callback", req.model_dump(), response)
        return response

    async def handle_money_callback(self, req: SeamlessMoneyCallbackRequest) -> dict[str, Any]:
        key_material = f"{req.user_code}:{req.provider_code}:{req.game_code}:{req.type}:{req.amount}:{req.user_before_balance}:{req.user_after_balance}:{req.created_at or ''}"
        event_key = f"money_callback:{key_material}"
        existing = await self._get_existing_event(event_key)
        if existing:
            response = dict(existing.get("response") or {})
            response.setdefault("status", 1)
            response.setdefault("idempotent", True)
            return response

        player = await self._get_player(req.user_code)
        if not player:
            response = {"status": 0, "msg": "USER_NOT_FOUND"}
            await self._record_event(event_key, "money_callback", req.model_dump(), response)
            return response

        current_balance = wallet_ledger.money_to_decimal(player.get("wallet_balance", 0), self.currency)
        action = (req.type or "").lower()
        amount = wallet_ledger.money_to_decimal(req.amount or 0, self.currency)
        if action in {"debit_credit", "adjustment"} and req.user_before_balance is not None and req.user_after_balance is not None:
            before = wallet_ledger.money_to_decimal(req.user_before_balance, self.currency)
            after = wallet_ledger.money_to_decimal(req.user_after_balance, self.currency)
            amount = abs(after - before)
            action = "credit" if after >= before else "debit"

        credit_actions = {"deposit", "credit", "refund", "rollback", "cancel"}
        debit_actions = {"withdraw", "withdrawal", "debit"}
        if action in credit_actions:
            new_balance = await wallet_ledger.atomic_credit(
                self.db,
                tenant_id=self.tenant_id,
                player_id=req.user_code,
                amount=amount,
                currency=self.currency,
            )
            tx_type = "deposit" if action == "deposit" else "adjustment"
            balance_before = current_balance
            balance_after = current_balance + amount
        elif action in debit_actions:
            if amount > current_balance:
                response = {"status": 0, "msg": "INSUFFICIENT_USER_FUNDS"}
                await self._record_event(event_key, "money_callback", req.model_dump(), response)
                return response
            new_balance = await wallet_ledger.atomic_debit(
                self.db,
                tenant_id=self.tenant_id,
                player_id=req.user_code,
                amount=amount,
                currency=self.currency,
            )
            tx_type = "withdrawal" if action in {"withdraw", "withdrawal"} else "adjustment"
            balance_before = current_balance
            balance_after = current_balance - amount
        else:
            response = {"status": 0, "msg": f"UNSUPPORTED_TYPE:{req.type}"}
            await self._record_event(event_key, "money_callback", req.model_dump(), response)
            return response

        if new_balance is None:
            response = {"status": 0, "msg": "TRANSACTION_FAILED"}
            await self._record_event(event_key, "money_callback", req.model_dump(), response)
            return response

        await self._record_transaction(
            tx_id=f"money:{event_key}",
            tx_type=tx_type,
            player_id=req.user_code,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            game_code=req.game_code,
            provider_code=req.provider_code,
            metadata={"money_type": req.type, "message": req.msg},
        )
        response = {"status": 1, "msg": "SUCCESS"}
        await self._record_event(event_key, "money_callback", req.model_dump(), response)
        return response


async def resolve_tenant_from_seamless_agent_code(db, agent_code: str) -> tuple[dict[str, Any], dict[str, Any]]:
    tenant = await db.tenants.find_one(
        {"provider_config.seamless.enabled": True, "provider_config.seamless.agent_code": agent_code},
        {"_id": 0},
    )
    if not tenant:
        raise LookupError(f"Unknown seamless agent_code: {agent_code}")
    config = tenant.get("provider_config", {}).get("seamless", {})
    return tenant, config
