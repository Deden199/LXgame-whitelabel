from abc import ABC, abstractmethod
from typing import Any, Dict


class BasePaymentAdapter(ABC):
    @abstractmethod
    async def create_deposit(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def create_withdraw(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def verify_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError
