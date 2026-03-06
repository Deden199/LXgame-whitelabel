"""VD7 Aggregator - Outbound Adapter.

Handles outbound calls to VD7:
- Client authentication (OAuth2 token)
- Player authorization
- Game launch URL generation (OpenGame)
- Game list with icons

This adapter implements the GameProviderAdapter interface.
STRICT compliance with VD7 API documentation (egs777.pdf).

NOTE: Uses NordVPN HTTP Proxy for IP whitelisting requirements.
"""

from __future__ import annotations

import os
import uuid
import httpx
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from .base import GameProviderAdapter

logger = logging.getLogger(__name__)

# Default VD7 API base URL (can be overridden via env)
VD7_API_BASE_URL = os.environ.get("VD7_API_BASE_URL", "https://api.vd7.xyz")

# NordVPN Proxy configuration for IP whitelisting
# Dedicated IP: 89.35.54.224
NORDVPN_PROXY_HOST = os.environ.get("NORDVPN_PROXY_HOST", "sg632.nordvpn.com")
NORDVPN_PROXY_PORT = int(os.environ.get("NORDVPN_PROXY_PORT", "89"))
NORDVPN_PROXY_USER = os.environ.get("NORDVPN_PROXY_USER", "DRXqyL4AhkneqEEom5kN71ru")
NORDVPN_PROXY_PASS = os.environ.get("NORDVPN_PROXY_PASS", "7qEhYMpqKr9NPFAJsEp7HG76")
VD7_USE_PROXY = os.environ.get("VD7_USE_PROXY", "true").lower() == "true"
VD7_WHITELISTED_IP = os.environ.get("VD7_WHITELISTED_IP", "89.35.54.224")

# Module-level token cache keyed by (client_id, scope)
# Structure: { "client_id_scope": {"token": str, "expires_at": datetime} }
_token_cache: Dict[str, Dict[str, Any]] = {}


def get_vd7_http_client(timeout: float = 30.0) -> httpx.AsyncClient:
    """Get HTTP client with optional NordVPN proxy for VD7 API calls."""
    if VD7_USE_PROXY:
        proxy_url = f"https://{NORDVPN_PROXY_USER}:{NORDVPN_PROXY_PASS}@{NORDVPN_PROXY_HOST}:{NORDVPN_PROXY_PORT}"
        logger.debug(f"VD7 using proxy: {NORDVPN_PROXY_HOST}:{NORDVPN_PROXY_PORT}")
        # Use limits to force new connections each time
        # This helps avoid connection reuse issues with proxy
        limits = httpx.Limits(max_keepalive_connections=0, max_connections=10)
        return httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=15.0),
            proxy=proxy_url,
            verify=False,  # Required for NordVPN proxy SSL
            limits=limits,
            http2=False,  # Force HTTP/1.1 for proxy compatibility
        )
    else:
        return httpx.AsyncClient(timeout=timeout)


class VD7Adapter(GameProviderAdapter):
    """VD7 Aggregator adapter for game launching and player management."""
    
    def __init__(
        self,
        api_base_url: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        agent_code: Optional[str] = None,
        agent_secret: Optional[str] = None,
    ):
        """
        Initialize VD7 adapter.
        
        For multi-tenant: pass tenant-specific credentials.
        For global: use environment variables.
        """
        self.api_base_url = api_base_url or VD7_API_BASE_URL
        self.client_id = client_id or os.environ.get("VD7_CLIENT_ID", "")
        self.client_secret = client_secret or os.environ.get("VD7_CLIENT_SECRET", "")
        self.agent_code = agent_code or os.environ.get("VD7_AGENT_CODE", "")
        self.agent_secret = agent_secret or os.environ.get("VD7_AGENT_SECRET", "")
    
    @property
    def provider_id(self) -> str:
        return "vd7"
    
    @property
    def provider_name(self) -> str:
        return "VD7 Aggregator"
    
    async def _get_client_token(self, scope: str = "player:authorization") -> str:
        """Get OAuth2 access token for API calls.
        
        Caches token until expiry using module-level cache.
        Uses x-www-form-urlencoded format as required by VD7 API.
        
        Args:
            scope: Token scope - "player:authorization" for game launch, 
                   "client:action" for gamelist/admin operations
        """
        global _token_cache
        
        # Check module-level cache (keyed by client_id + scope)
        cache_key = f"{self.client_id}_{scope}"
        if cache_key in _token_cache:
            cached = _token_cache[cache_key]
            if datetime.now(timezone.utc) < cached['expires_at']:
                logger.debug(f"VD7 token cache hit: scope={scope}")
                return cached['token']
        
        # Request new token using x-www-form-urlencoded format
        url = f"{self.api_base_url}/api/v1/oauth2/token"
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
            "scope": scope,
        }
        
        logger.info(f"VD7 OAuth2: POST {url} (scope={scope})")
        
        async with get_vd7_http_client(timeout=30.0) as client:
            response = await client.post(
                url, 
                data=payload,  # data= for form-urlencoded
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            logger.info(f"VD7 OAuth2 response: status={response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"VD7 OAuth2 HTTP error: {response.status_code} - {response.text}")
                response.raise_for_status()
            
            data = response.json()
        
        logger.info(f"VD7 OAuth2 response: code={data.get('code', 'N/A')}, msg={data.get('msg', 'N/A')}, trace_id={data.get('trace_id', 'N/A')}")
        
        # Check for VD7 error response
        if "code" in data and data.get("code") != 0:
            raise Exception(f"VD7 OAuth2 failed: {data.get('msg')} (code={data.get('code')}, trace_id={data.get('trace_id')})")
        
        access_token = data.get("access_token")
        if not access_token:
            raise Exception(f"VD7 OAuth2 failed: No access_token in response")
        
        # Cache token (module-level cache)
        expires_in = int(data.get("expires_in", 3600))
        _token_cache[cache_key] = {
            'token': access_token,
            'expires_at': datetime.now(timezone.utc) + timedelta(seconds=min(expires_in, 86400) - 60)
        }
        
        logger.info(f"VD7 client token obtained (scope={scope}), expires in {expires_in}s")
        return access_token
    
    async def authorize_player(
        self,
        player_id: str,
        currency_code: str,
        ip_address: str,
        is_test_player: bool = True,
    ) -> Dict[str, Any]:
        """Authorize player and get player token.
        
        Per VD7 API docs:
        - POST /api/v1/player/authorize
        - Content-Type: application/x-www-form-urlencoded
        - Authorization: Bearer <client_token>
        
        Args:
            player_id: Internal player ID (used to build username)
            currency_code: Player's currency (e.g., "IDR", "TRY")
            ip_address: Player's PUBLIC IP address (must be whitelisted)
            is_test_player: Whether this is a test player (from tenant config)
            
        Returns:
            {
                "auth_token": str,  # Player token for game launch
                "expire_in": int,   # Token expiry in seconds
            }
        """
        access_token = await self._get_client_token(scope="player:authorization")
        
        # Username format per API docs:
        # - Must be stable (same player_id always produces same username)
        # - Only remove hyphens (for UUID compatibility)
        # - DO NOT remove underscores
        # - DO NOT truncate aggressively
        # - Prefix with agent_code as per VD7 convention
        # - Max 50 chars (VD7 API limit)
        clean_player = player_id.replace("-", "")  # Remove hyphens only
        vd7_username = f"{self.agent_code}_{clean_player}"
        
        # Truncate only if necessary (max 50 chars per docs)
        if len(vd7_username) > 50:
            max_player_len = 50 - len(self.agent_code) - 1
            vd7_username = f"{self.agent_code}_{clean_player[:max_player_len]}"
        
        url = f"{self.api_base_url}/api/v1/player/authorize"
        
        # CRITICAL: is_test_player must be boolean for JSON format
        # This comes from tenant.provider_config.vd7.is_test_player
        # NEVER hardcode - must be configurable
        payload = {
            "username": vd7_username,
            "currency_code": currency_code,
            "is_test_player": is_test_player,  # Boolean for JSON
            "ipaddress": ip_address,
        }
        
        logger.info(f"VD7 authorize_player: POST {url}")
        logger.info(f"VD7 authorize_player payload: username={vd7_username}, currency={currency_code}, is_test_player={payload['is_test_player']}, ip={ip_address}")
        
        async with get_vd7_http_client(timeout=30.0) as client:
            response = await client.post(
                url,
                json=payload,  # Use JSON content type for player authorization
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }
            )
            
            logger.info(f"VD7 authorize_player response: status={response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"VD7 authorize_player HTTP error: {response.status_code} - {response.text}")
            
            response.raise_for_status()
            data = response.json()
        
        # Log full response with trace_id
        logger.info(f"VD7 authorize_player response: code={data.get('code')}, msg={data.get('msg')}, trace_id={data.get('trace_id')}")
        
        if data.get("code") != 0:
            error_code = data.get("code")
            error_msg = data.get("msg")
            trace_id = data.get("trace_id", "N/A")
            
            # Specific error handling
            if error_code == 102:
                logger.error(f"VD7 invalid_player (102): Check username format. trace_id={trace_id}")
            elif error_code == 104:
                logger.error(f"VD7 invalid_ip (104): IP {ip_address} not whitelisted. trace_id={trace_id}")
            
            raise Exception(f"VD7 player authorization failed: {error_msg} (code={error_code}, trace_id={trace_id})")
        
        logger.info(f"VD7 authorize_player success: expires in {data.get('expire_in', 3600)}s, is_new={data.get('is_new')}")
        
        auth_token = data.get("auth_token")
        logger.info(f"VD7 authorize_player auth_token length: {len(auth_token) if auth_token else 0}")
        
        return {
            "auth_token": auth_token,
            "expire_in": data.get("expire_in", 3600),
        }
    
    async def create_session(
        self,
        player_id: str,
        game_id: str,
        tenant_id: str,
        currency: str = "IDR",
        language: str = "en",
        **kwargs
    ) -> Dict[str, Any]:
        """Create game session via VD7 OpenGame API.
        
        Per VD7 API docs:
        - POST /api/v1/game/opengame
        - Authorization: Bearer <player_token>
        
        Args:
            player_id: Internal player ID
            game_id: VD7 game_launch_id (from game.game_launch_id)
            tenant_id: Tenant ID for config lookup
            currency: Player's currency
            language: Game language
            **kwargs:
                ip_address: Player's PUBLIC IP (required, must be whitelisted)
                home_url: Return URL
                platform: "1"=Desktop, "2"=Mobile H5, "3"=Mobile Desktop
                provider_code: Game provider code (required)
                is_test_player: From tenant config (required)
            
        Returns:
            {
                "session_id": str,
                "launch_url": str,
                "expires_at": datetime
            }
        """
        ip_address = kwargs.get("ip_address", "127.0.0.1")
        home_url = kwargs.get("home_url", "")
        # Platform per API docs: "1" for desktop, "2" for mobile H5
        # VD7 API requires numeric string
        platform = kwargs.get("platform", "1")
        # Convert any text platform to numeric
        platform_map = {
            "web": "1",
            "desktop": "1",
            "mobile": "2",
            "desktop & mobile": "1",  # Default to desktop
            "1": "1",
            "2": "2",
        }
        platform = platform_map.get(str(platform).lower().strip(), "1")
        
        provider_code = kwargs.get("provider_code", "")
        # CRITICAL: is_test_player must come from caller (tenant config)
        is_test_player = kwargs.get("is_test_player", True)
        
        logger.info(f"VD7 create_session: player={player_id}, game={game_id}, provider={provider_code}, is_test_player={is_test_player}, ip={ip_address}")
        
        # Verify proxy is working by checking outgoing IP
        try:
            async with get_vd7_http_client(timeout=10.0) as ip_client:
                ip_resp = await ip_client.get("https://api.ipify.org")
                outgoing_ip = ip_resp.text.strip()
                logger.info(f"VD7 create_session: outgoing IP via proxy = {outgoing_ip}")
        except Exception as e:
            logger.warning(f"VD7 create_session: could not verify outgoing IP: {e}")
        
        # Get player token
        player_auth = await self.authorize_player(player_id, currency, ip_address, is_test_player=is_test_player)
        player_token = player_auth["auth_token"]
        
        # Generate session ID
        session_id = f"vd7_{uuid.uuid4().hex[:16]}"
        agent_session_id = f"{self.agent_code}_{tenant_id[:8]}_{session_id}"
        
        # Build OpenGame request - per API docs: /api/v1/game/opengame
        # Authorization header uses CLIENT token (from Client Auth API)
        # player_token goes in the BODY (x-www-form-urlencoded)
        access_token = await self._get_client_token(scope="player:authorization")
        
        url = f"{self.api_base_url}/api/v1/game/opengame"
        payload = {
            "player_token": player_token,  # Required in body per API docs
            "provider_code": provider_code,
            "game_launch_id": game_id,
            "platform": platform,
            "language": language,
            "home_url": home_url,
            "agent_session_id": agent_session_id,
        }
        
        logger.info(f"VD7 openGame: POST {url}")
        logger.info(f"VD7 openGame payload: provider_code={provider_code}, game_launch_id={game_id}, platform={platform}, agent_session_id={agent_session_id}")
        logger.debug(f"VD7 openGame player_token length: {len(player_token) if player_token else 0}")
        logger.debug(f"VD7 openGame access_token length: {len(access_token) if access_token else 0}")
        
        # Retry logic for intermittent 305 errors
        max_retries = 3
        retry_delay = 1.0
        last_error = None
        
        for attempt in range(max_retries):
            try:
                async with get_vd7_http_client(timeout=30.0) as client:
                    response = await client.post(
                        url,
                        data=payload,  # Must use x-www-form-urlencoded per API docs
                        headers={
                            "Authorization": f"Bearer {access_token}",  # Use CLIENT token in header
                            "Content-Type": "application/x-www-form-urlencoded"
                        }
                    )
                    
                    logger.info(f"VD7 openGame response: status={response.status_code} (attempt {attempt + 1})")
                    
                    if response.status_code != 200:
                        logger.error(f"VD7 openGame HTTP error: {response.status_code} - {response.text}")
                    
                    response.raise_for_status()
                    data = response.json()
                
                # Log full response with trace_id
                logger.info(f"VD7 openGame response: code={data.get('code')}, msg={data.get('msg')}, trace_id={data.get('trace_id')}")
                
                if data.get("code") == 0:
                    # Success!
                    break
                elif data.get("code") in [305, 308]:
                    # Provider error - may be temporary, retry
                    error_code = data.get("code")
                    error_msg = data.get("msg")
                    trace_id = data.get("trace_id", "N/A")
                    last_error = f"VD7 OpenGame failed: {error_msg} (code={error_code}, trace_id={trace_id})"
                    logger.warning(f"VD7 OpenGame attempt {attempt + 1} failed: {error_msg} (code={error_code}), retrying in {retry_delay}s...")
                    
                    # Clear token cache and wait before retry
                    _token_cache.clear()
                    import asyncio
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 1.5  # Exponential backoff
                    
                    # Get fresh tokens for retry
                    player_auth = await self.authorize_player(player_id, currency, ip_address, is_test_player=is_test_player)
                    player_token = player_auth["auth_token"]
                    access_token = await self._get_client_token(scope="player:authorization")
                    payload["player_token"] = player_token
                    continue
                else:
                    # Other error - don't retry
                    error_code = data.get("code")
                    error_msg = data.get("msg")
                    trace_id = data.get("trace_id", "N/A")
                    raise Exception(f"VD7 OpenGame failed: {error_msg} (code={error_code}, trace_id={trace_id})")
                    
            except Exception as e:
                if "VD7 OpenGame failed" in str(e):
                    raise
                last_error = str(e)
                logger.error(f"VD7 openGame attempt {attempt + 1} exception: {e}")
                if attempt < max_retries - 1:
                    import asyncio
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 1.5
        else:
            # All retries exhausted
            raise Exception(last_error or "VD7 OpenGame failed after retries")
        
        launch_url = data.get("url") or data.get("launch_url", "")
        expires_at = datetime.now(timezone.utc) + timedelta(hours=2)
        
        logger.info(f"VD7 game session created: session={session_id}, url={launch_url[:80]}...")
        
        return {
            "session_id": session_id,
            "launch_url": launch_url,
            "expires_at": expires_at,
            "player_token": player_token,
        }
    
    async def get_launch_url(self, session_id: str) -> str:
        """Get launch URL for existing session.
        
        Note: VD7 doesn't support fetching URL by session.
        This returns a placeholder.
        """
        logger.warning(f"VD7 get_launch_url not supported, session={session_id}")
        return ""
    
    async def handle_callback(
        self,
        action: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle provider callbacks.
        
        Note: VD7 callbacks are handled by dedicated endpoints in server.py,
        not through this adapter method.
        """
        logger.warning("VD7 handle_callback called directly - use dedicated endpoints")
        return {
            "success": False,
            "error": "Use dedicated VD7 callback endpoints"
        }
    
    async def validate_session(self, session_id: str) -> bool:
        """Validate session.
        
        VD7 doesn't have a session validation endpoint.
        """
        return True
    
    async def close_session(self, session_id: str) -> bool:
        """Close session.
        
        VD7 doesn't have a session close endpoint.
        """
        return True
    
    async def get_games(
        self,
        provider_code: str,
        page: int = 1,
        page_size: int = 1000,
    ) -> Dict[str, Any]:
        """Fetch game list from VD7 with icons.
        
        Per API docs: POST /api/v1/game/gamelist
        - Authorization: Bearer <client_token> (scope: client:action)
        - Content-Type: application/x-www-form-urlencoded
        
        IMPORTANT: API may or may not accept comma-separated provider_codes.
        Per docs, provider_code parameter is required.
        If API returns error for CSV list, caller should loop per provider.
        
        Response includes mobileImgUrl and pcImgUrl for each game.
        
        Args:
            provider_code: REQUIRED - single provider code (e.g., "FC")
            page: Page number for pagination
            page_size: Number of records per page (max 1000)
            
        Returns:
            Dict with games list and pagination info
            
        Raises:
            ValueError: If provider_code is empty (required by API docs)
        """
        if not provider_code or not provider_code.strip():
            raise ValueError("provider_code is REQUIRED by VD7 API docs. Configure tenant.provider_config.vd7.provider_codes or env VD7_PROVIDER_CODES")
        
        # Use client:action scope for gamelist endpoint per API docs
        access_token = await self._get_client_token(scope="client:action")
        
        url = f"{self.api_base_url}/api/v1/game/gamelist"
        payload = {
            "provider_code": provider_code.strip(),
            "page": str(page),
            "page_size": str(page_size),
        }
        
        logger.info(f"VD7 get_games: POST {url} provider_code={provider_code} page={page} page_size={page_size}")
        
        async with get_vd7_http_client(timeout=60.0) as client:
            response = await client.post(
                url,
                data=payload,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/x-www-form-urlencoded"
                }
            )
            
            logger.info(f"VD7 get_games response: status={response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"VD7 get_games HTTP error: {response.status_code} - {response.text}")
            
            response.raise_for_status()
            data = response.json()
        
        # Log response with trace_id
        code = data.get("code")
        msg = data.get("msg")
        trace_id = data.get("trace_id", "N/A")
        total_records = data.get("total_records", 0)
        
        logger.info(f"VD7 get_games response: code={code}, msg={msg}, trace_id={trace_id}, total_records={total_records}")
        
        # Handle specific error codes
        if code == 114:
            # Record Not Found - not an error, just empty result
            logger.warning(f"VD7 get_games: No games found for provider_code={provider_code}")
            return {
                "games": [],
                "total_records": 0,
                "total_pages": 0,
                "current_page": page,
                "page_size": page_size,
                "error_code": 114,
            }
        
        if code != 0:
            raise Exception(f"VD7 game list failed: {msg} (code={code}, trace_id={trace_id})")
        
        # Parse games with icon URLs
        games = []
        for game in data.get("games", []):
            games.append({
                "id": game.get("id"),
                "provider_code": game.get("providerCode"),
                "provider_name": game.get("providerName"),
                "game_code": game.get("gameCode"),
                "game_name": game.get("gameName"),
                "category": game.get("categoryName"),
                "platform": game.get("platform"),
                "is_free_spin": game.get("isFreeSpin", False),
                "status": game.get("status"),
                "currency_codes": game.get("currencyCode", "").split(","),
                "mobile_img_url": game.get("mobileImgUrl"),
                "pc_img_url": game.get("pcImgUrl"),
                "remark": game.get("remark"),
            })
        
        return {
            "games": games,
            "total_records": int(data.get("total_records", 0)),
            "total_pages": int(data.get("total_pages", 0)),
            "current_page": int(data.get("current_page", 1)),
            "page_size": int(data.get("page_size", page_size)),
        }


def create_vd7_adapter_for_tenant(tenant_config: dict) -> Optional[VD7Adapter]:
    """Factory to create VD7 adapter from tenant config.
    
    Args:
        tenant_config: Tenant's provider_config.vd7 dict
        
    Returns:
        Configured VD7Adapter or None if disabled
    """
    if not tenant_config or not tenant_config.get("enabled"):
        return None
    
    return VD7Adapter(
        agent_code=tenant_config.get("agent_code"),
        agent_secret=tenant_config.get("agent_secret"),
        client_id=tenant_config.get("client_id"),
        client_secret=tenant_config.get("client_secret"),
        api_base_url=tenant_config.get("api_base_url"),
    )
