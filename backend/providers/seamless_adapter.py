from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

from catalog_normalization import derive_game_type
from providers.base import GameProviderAdapter


class SeamlessAdapter(GameProviderAdapter):
    def __init__(
        self,
        *,
        api_base_url: Optional[str] = None,
        agent_code: Optional[str] = None,
        agent_token: Optional[str] = None,
        agent_secret: Optional[str] = None,
        timeout_seconds: int = 20,
    ):
        self.api_base_url = (api_base_url or os.environ.get("SEAMLESS_API_BASE_URL") or "https://svc-v1.lunexa.to").rstrip("/")
        self.agent_code = agent_code or os.environ.get("SEAMLESS_AGENT_CODE") or ""
        self.agent_token = agent_token or os.environ.get("SEAMLESS_AGENT_TOKEN") or ""
        self.agent_secret = agent_secret or os.environ.get("SEAMLESS_AGENT_SECRET") or ""
        self.timeout_seconds = timeout_seconds

    @property
    def provider_id(self) -> str:
        return "seamless"

    @property
    def provider_name(self) -> str:
        return "Seamless Source"

    def is_configured_for_launch(self) -> bool:
        return not self.missing_launch_config()

    def missing_launch_config(self) -> list[str]:
        missing = []
        if not self.api_base_url:
            missing.append("SEAMLESS_API_BASE_URL")
        if not self.agent_code:
            missing.append("SEAMLESS_AGENT_CODE")
        if not self.agent_token:
            missing.append("SEAMLESS_AGENT_TOKEN")
        return missing

    def build_launch_payload(
        self,
        *,
        user_code: str,
        user_balance: int | float,
        provider_code: str,
        game_code: str,
        category: str,
        language: str = "en",
    ) -> dict[str, Any]:
        return {
            "agent_code": self.agent_code,
            "agent_token": self.agent_token,
            "user_code": user_code,
            "game_type": derive_game_type(category),
            "provider_code": provider_code,
            "game_code": game_code,
            "lang": language,
            "user_balance": user_balance,
        }

    def launch_contract_preview(
        self,
        *,
        user_code: str,
        user_balance: int | float,
        provider_code: str,
        game_code: str,
        category: str,
        language: str = "en",
    ) -> dict[str, Any]:
        payload = self.build_launch_payload(
            user_code=user_code,
            user_balance=user_balance,
            provider_code=provider_code,
            game_code=game_code,
            category=category,
            language=language,
        )
        return {
            "mode": "live" if self.is_configured_for_launch() else "contract_only",
            "endpoint": f"{self.api_base_url}/api/v2/game_launch",
            "payload": payload,
            "missing_config": self.missing_launch_config(),
        }

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(f"{self.api_base_url}{path}", json=payload)
            response.raise_for_status()
            return response.json()

    async def fetch_info(self) -> dict[str, Any]:
        payload = {"agent_code": self.agent_code, "agent_token": self.agent_token}
        return await self._post("/api/v2/info", payload)

    async def fetch_provider_list(self, game_type: str = "slot") -> dict[str, Any]:
        payload = {"agent_code": self.agent_code, "agent_token": self.agent_token, "game_type": game_type}
        return await self._post("/api/v2/provider_list", payload)

    async def fetch_game_list(self, provider_code: str, lang: str = "en") -> dict[str, Any]:
        payload = {
            "agent_code": self.agent_code,
            "agent_token": self.agent_token,
            "provider_code": provider_code,
            "lang": lang,
        }
        return await self._post("/api/v2/game_list", payload)

    async def get_log_detail(self, provider_code: str, round_id: str) -> dict[str, Any]:
        payload = {
            "agent_code": self.agent_code,
            "agent_token": self.agent_token,
            "provider_code": provider_code,
            "round_id": round_id,
        }
        return await self._post("/api/v2/get_log_detail", payload)

    async def create_session(
        self,
        player_id: str,
        game_id: str,
        tenant_id: str,
        currency: str = "USD",
        language: str = "en",
        **kwargs,
    ) -> dict[str, Any]:
        category = kwargs.get("category", "slots")
        provider_code = kwargs.get("provider_code") or ""
        user_balance = kwargs.get("user_balance", 0)
        preview = self.launch_contract_preview(
            user_code=player_id,
            user_balance=user_balance,
            provider_code=provider_code,
            game_code=game_id,
            category=category,
            language=language,
        )
        if preview["missing_config"]:
            missing = ", ".join(preview["missing_config"])
            raise ValueError(f"Seamless launch unavailable: missing config {missing}")
        data = await self._post("/api/v2/game_launch", preview["payload"])
        if data.get("status") != 1 or not data.get("launch_url"):
            raise ValueError(data.get("msg") or "Seamless launch failed")
        return {
            "session_id": kwargs.get("session_id") or f"seamless_{tenant_id}_{player_id}_{game_id}_{int(datetime.now(timezone.utc).timestamp())}",
            "launch_url": data["launch_url"],
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=2),
            "provider_response": data,
            "request_payload": preview["payload"],
        }

    async def get_launch_url(self, session_id: str) -> str:
        return ""

    async def handle_callback(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {"success": False, "error": f"Use dedicated seamless callback endpoints for {action}", "payload": payload}

    async def validate_session(self, session_id: str) -> bool:
        return True

    async def close_session(self, session_id: str) -> bool:
        return True


def create_seamless_adapter_for_tenant(provider_config: dict | None) -> SeamlessAdapter | None:
    provider_config = provider_config or {}
    seamless_config = provider_config.get("seamless") if "seamless" in provider_config else provider_config
    if not isinstance(seamless_config, dict):
        return None
    if not seamless_config.get("enabled", True):
        return None
    return SeamlessAdapter(
        api_base_url=seamless_config.get("api_base_url"),
        agent_code=seamless_config.get("agent_code"),
        agent_token=seamless_config.get("agent_token"),
        agent_secret=seamless_config.get("agent_secret"),
        timeout_seconds=int(seamless_config.get("timeout_seconds", 20)),
    )
