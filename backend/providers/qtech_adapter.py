from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from urllib.parse import urlencode

from .base import GameProviderAdapter
from .mock import MockProviderAdapter


class QTechAdapter(GameProviderAdapter):
    def __init__(self):
        self.mode = os.environ.get("QTECH_MODE", "demo").strip().lower()
        self.launch_base_url = os.environ.get("QTECH_LAUNCH_URL", "https://aggregator.example/launch")
        self.operator_token = os.environ.get("QTECH_OPERATOR_TOKEN", "demo-token")
        self.mock_adapter = MockProviderAdapter()

    @property
    def provider_id(self) -> str:
        return "qtech"

    @property
    def provider_name(self) -> str:
        return "QTech Aggregator"

    async def create_session(
        self,
        player_id: str,
        game_id: str,
        tenant_id: str,
        currency: str = "USD",
        language: str = "en",
        **kwargs,
    ) -> Dict[str, Any]:
        if self.mode != "real":
            return await self.mock_adapter.create_session(
                player_id=player_id,
                game_id=game_id,
                tenant_id=tenant_id,
                currency=currency,
                language=language,
                **kwargs,
            )

        session_id = f"qtech_{uuid.uuid4().hex[:16]}"
        expires_at = datetime.now(timezone.utc) + timedelta(hours=2)
        payload = {
            "operatorToken": self.operator_token,
            "playerId": player_id,
            "gameId": game_id,
            "tenantId": tenant_id,
            "currency": currency,
            "lang": language,
            "sessionId": session_id,
            "timestamp": int(datetime.now(timezone.utc).timestamp()),
        }
        launch_url = f"{self.launch_base_url}?{urlencode(payload)}"
        return {"session_id": session_id, "launch_url": launch_url, "expires_at": expires_at}

    async def get_launch_url(self, session_id: str) -> str:
        if self.mode != "real":
            return await self.mock_adapter.get_launch_url(session_id)
        return f"{self.launch_base_url}?sessionId={session_id}"

    async def handle_callback(self, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if self.mode != "real":
            return await self.mock_adapter.handle_callback(action, payload)
        return {
            "success": True,
            "balance": payload.get("current_balance", 0),
            "tx_id": payload.get("tx_id") or f"qtech_{uuid.uuid4().hex[:12]}",
        }

    async def validate_session(self, session_id: str) -> bool:
        if self.mode != "real":
            return await self.mock_adapter.validate_session(session_id)
        return True

    async def close_session(self, session_id: str) -> bool:
        if self.mode != "real":
            return await self.mock_adapter.close_session(session_id)
        return True
