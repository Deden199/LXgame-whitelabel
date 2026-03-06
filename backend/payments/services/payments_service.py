"""Payment service with enhanced security.

Features:
- Idempotency scoped by (provider, tenant_id, event_id)
- Event tracking with deduplication
"""

from __future__ import annotations

from datetime import datetime, timezone

from payments.adapters.dummy import DummyPaymentAdapter


class PaymentsService:
    def __init__(self, db):
        self.db = db
        self.adapters = {
            'dummy': DummyPaymentAdapter(),
        }

    def adapter(self, provider: str):
        return self.adapters.get(provider, self.adapters['dummy'])

    async def record_event_if_new(self, event: dict):
        """Record payment event with proper scoped idempotency.
        
        Idempotency is scoped by (provider, tenant_id, event_id) to prevent
        cross-tenant event collisions.
        
        Returns:
            Tuple of (event_data, is_duplicate)
        """
        # Build idempotency key if not provided
        idempotency_key = event.get('idempotency_key')
        if not idempotency_key:
            idempotency_key = f"{event.get('provider', 'unknown')}:{event.get('tenant_id', '')}:{event['event_id']}"
            event['idempotency_key'] = idempotency_key
        
        # Check for existing event using idempotency key
        existing = await self.db.payment_events.find_one(
            {'idempotency_key': idempotency_key},
            {'_id': 0}
        )
        
        if existing:
            return existing, True
        
        # Also check by original event_id + tenant_id for backward compatibility
        existing_legacy = await self.db.payment_events.find_one(
            {
                'event_id': event['event_id'],
                'tenant_id': event.get('tenant_id'),
                'provider': event.get('provider'),
            },
            {'_id': 0}
        )
        
        if existing_legacy:
            return existing_legacy, True
        
        event['created_at'] = datetime.now(timezone.utc).isoformat()
        await self.db.payment_events.insert_one(event)
        event.pop('_id', None)
        return event, False
