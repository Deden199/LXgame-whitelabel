import secrets
from typing import Any, Dict

from .base import BasePaymentAdapter


class DummyPaymentAdapter(BasePaymentAdapter):
    async def create_deposit(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        order_id = payload['order_id']
        return {
            'provider_order_id': f"dep_{order_id}",
            'checkout_url': f"https://dummy-pay.local/checkout/{order_id}",
            'status': 'pending',
        }

    async def create_withdraw(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        order_id = payload['order_id']
        return {
            'provider_order_id': f"wd_{order_id}",
            'reference': secrets.token_hex(8),
            'status': 'processing',
        }

    async def verify_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return payload
