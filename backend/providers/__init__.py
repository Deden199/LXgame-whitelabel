# Provider Adapter Architecture
# This module contains the provider adapter interface and implementations

from .base import GameProviderAdapter, ProviderRegistry, provider_registry
from .mock import MockProviderAdapter
from .pragmatic import PragmaticPlayAdapter
from .pgsoft import PGSoftAdapter
from .qtech_adapter import QTechAdapter
from .vd7_adapter import VD7Adapter, create_vd7_adapter_for_tenant
from .seamless_adapter import SeamlessAdapter, create_seamless_adapter_for_tenant

__all__ = [
    "GameProviderAdapter",
    "ProviderRegistry",
    "provider_registry",
    "MockProviderAdapter",
    "PragmaticPlayAdapter",
    "PGSoftAdapter",
    "QTechAdapter",
    "VD7Adapter",
    "create_vd7_adapter_for_tenant",
    "SeamlessAdapter",
    "create_seamless_adapter_for_tenant",
]
