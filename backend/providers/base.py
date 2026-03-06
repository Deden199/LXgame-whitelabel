from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
from datetime import datetime, timezone
import uuid


class GameProviderAdapter(ABC):
    """
    Base interface for game provider adapters.
    All provider integrations (Pragmatic, PGSoft, etc.) must implement this interface.
    """
    
    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique identifier for this provider"""
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name"""
        pass
    
    @abstractmethod
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
        Create a game session for the player.
        
        Returns:
            {
                "session_id": str,
                "launch_url": str,
                "expires_at": datetime (optional)
            }
        """
        pass
    
    @abstractmethod
    async def get_launch_url(self, session_id: str) -> str:
        """
        Get the launch URL for an existing session.
        """
        pass
    
    @abstractmethod
    async def handle_callback(
        self,
        action: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle provider callbacks (bet, win, rollback).
        
        Args:
            action: "bet", "win", or "rollback"
            payload: Provider-specific callback data
            
        Returns:
            {
                "success": bool,
                "balance": float,
                "tx_id": str
            }
        """
        pass
    
    @abstractmethod
    async def validate_session(self, session_id: str) -> bool:
        """
        Check if a session is still valid.
        """
        pass
    
    @abstractmethod
    async def close_session(self, session_id: str) -> bool:
        """
        Close/terminate a game session.
        """
        pass


class ProviderRegistry:
    """
    Registry for managing multiple game provider adapters.
    Singleton pattern to ensure single source of truth.
    """
    
    _instance: Optional["ProviderRegistry"] = None
    _providers: Dict[str, GameProviderAdapter] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._providers = {}
        return cls._instance
    
    def register(self, adapter: GameProviderAdapter) -> None:
        """Register a provider adapter"""
        self._providers[adapter.provider_id] = adapter
    
    def unregister(self, provider_id: str) -> None:
        """Unregister a provider adapter"""
        if provider_id in self._providers:
            del self._providers[provider_id]
    
    def get(self, provider_id: str) -> Optional[GameProviderAdapter]:
        """Get a provider adapter by ID"""
        return self._providers.get(provider_id)
    
    def get_all(self) -> Dict[str, GameProviderAdapter]:
        """Get all registered providers"""
        return self._providers.copy()
    
    def list_providers(self) -> list:
        """List all provider IDs and names"""
        return [
            {
                "id": p.provider_id,
                "name": p.provider_name
            }
            for p in self._providers.values()
        ]


# Global registry instance
provider_registry = ProviderRegistry()
