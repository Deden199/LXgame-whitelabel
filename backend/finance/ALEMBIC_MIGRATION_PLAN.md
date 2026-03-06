# Alembic Migration Plan for Tenant Finance

This document outlines the Alembic migration steps to deploy the Tenant Finance
schema to PostgreSQL (AWS RDS).

## Prerequisites

1. Install Alembic: `pip install alembic`
2. Configure database URL in `alembic.ini`
3. Ensure `tenants` table already exists

## Migration Files Structure

```
backend/
├── alembic/
│   ├── versions/
│   │   ├── 001_create_tenant_finance.py
│   │   └── 002_add_finance_indexes.py
│   ├── env.py
│   └── script.py.mako
├── alembic.ini
└── finance/
    └── postgres_schema.sql
```

## Migration 001: Create Tenant Finance Tables

**Filename**: `001_create_tenant_finance.py`

```python
"""Create tenant_finance and tenant_finance_tx tables.

Revision ID: 001_tenant_finance
Revises: (previous_migration)
Create Date: 2025-07-XX
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '001_tenant_finance'
down_revision = None  # or previous migration
branch_labels = None
depends_on = None


def upgrade():
    # tenant_finance table
    op.create_table(
        'tenant_finance',
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('buffer_balance_minor', sa.BigInteger, nullable=False, server_default='0'),
        sa.Column('buffer_min_threshold_minor', sa.BigInteger, nullable=False, server_default='25000000'),
        sa.Column('is_frozen', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('frozen_reason', sa.String(500), nullable=True),
        sa.Column('frozen_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ggr_share_percent', sa.Float, nullable=False, server_default='15.0'),
        sa.Column('infra_fee_monthly_minor', sa.BigInteger, nullable=False, server_default='5000000'),
        sa.Column('setup_fee_minor', sa.BigInteger, nullable=False, server_default='25000000'),
        sa.Column('setup_fee_mode', sa.String(20), nullable=False, server_default='ACTIVATION_DEPOSIT'),
        sa.Column('setup_fee_paid', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    
    # tenant_finance_tx table
    op.create_table(
        'tenant_finance_tx',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenant_finance.tenant_id', ondelete='CASCADE'), nullable=False),
        sa.Column('type', sa.String(20), nullable=False),
        sa.Column('amount_minor', sa.BigInteger, nullable=False),
        sa.Column('ref_id', sa.String(100), nullable=False),
        sa.Column('note', sa.String(500), nullable=True),
        sa.Column('fee_month', sa.String(7), nullable=True),
        sa.Column('setup_fee_mode', sa.String(20), nullable=True),
        sa.Column('created_by', sa.String(36), nullable=True),
        sa.Column('balance_after_minor', sa.BigInteger, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('tenant_id', 'ref_id', name='uq_tenant_finance_tx_ref_id'),
    )


def downgrade():
    op.drop_table('tenant_finance_tx')
    op.drop_table('tenant_finance')
```

## Migration 002: Add Indexes

**Filename**: `002_add_finance_indexes.py`

```python
"""Add indexes for tenant finance tables.

Revision ID: 002_finance_indexes
Revises: 001_tenant_finance
Create Date: 2025-07-XX
"""
from alembic import op

revision = '002_finance_indexes'
down_revision = '001_tenant_finance'
branch_labels = None
depends_on = None


def upgrade():
    # Index on frozen tenants (for admin dashboard)
    op.create_index(
        'idx_tenant_finance_frozen',
        'tenant_finance',
        ['is_frozen'],
        postgresql_where='is_frozen = true'
    )
    
    # Index on tenant + created_at for transaction listing
    op.create_index(
        'idx_tenant_finance_tx_tenant_created',
        'tenant_finance_tx',
        ['tenant_id', sa.text('created_at DESC')]
    )
    
    # Index on transaction type
    op.create_index(
        'idx_tenant_finance_tx_type',
        'tenant_finance_tx',
        ['type']
    )


def downgrade():
    op.drop_index('idx_tenant_finance_tx_type')
    op.drop_index('idx_tenant_finance_tx_tenant_created')
    op.drop_index('idx_tenant_finance_frozen')
```

## Migration 003: Add Updated_At Trigger

**Filename**: `003_add_updated_at_trigger.py`

```python
"""Add trigger for auto-updating updated_at column.

Revision ID: 003_updated_at_trigger
Revises: 002_finance_indexes
Create Date: 2025-07-XX
"""
from alembic import op

revision = '003_updated_at_trigger'
down_revision = '002_finance_indexes'
branch_labels = None
depends_on = None


def upgrade():
    # Create trigger function
    op.execute('''
        CREATE OR REPLACE FUNCTION update_tenant_finance_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    ''')
    
    # Create trigger
    op.execute('''
        CREATE TRIGGER trigger_tenant_finance_updated_at
            BEFORE UPDATE ON tenant_finance
            FOR EACH ROW
            EXECUTE FUNCTION update_tenant_finance_updated_at();
    ''')


def downgrade():
    op.execute('DROP TRIGGER IF EXISTS trigger_tenant_finance_updated_at ON tenant_finance')
    op.execute('DROP FUNCTION IF EXISTS update_tenant_finance_updated_at')
```

## Data Migration (Optional)

If migrating from MongoDB to PostgreSQL:

```python
"""Migrate tenant finance data from MongoDB.

Run after tables are created, before app goes live on Postgres.
"""

async def migrate_finance_from_mongo(mongo_db, pg_conn):
    \"\"\"One-time migration script.\"\"\"
    
    # Get all tenant_finance docs from MongoDB
    cursor = mongo_db.tenant_finance.find({})
    async for doc in cursor:
        await pg_conn.execute('''
            INSERT INTO tenant_finance (
                tenant_id, buffer_balance_minor, buffer_min_threshold_minor,
                is_frozen, frozen_reason, frozen_at,
                ggr_share_percent, infra_fee_monthly_minor,
                setup_fee_minor, setup_fee_mode, setup_fee_paid,
                created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            ON CONFLICT (tenant_id) DO NOTHING
        ''', 
            doc['tenant_id'],
            doc.get('buffer_balance_minor', 0),
            doc.get('buffer_min_threshold_minor', 25000000),
            doc.get('is_frozen', True),
            doc.get('frozen_reason'),
            doc.get('frozen_at'),
            doc.get('ggr_share_percent', 15.0),
            doc.get('infra_fee_monthly_minor', 5000000),
            doc.get('setup_fee_minor', 25000000),
            doc.get('setup_fee_mode', 'ACTIVATION_DEPOSIT'),
            doc.get('setup_fee_paid', False),
            doc.get('created_at'),
            doc.get('updated_at'),
        )
    
    # Migrate transactions
    cursor = mongo_db.tenant_finance_tx.find({})
    async for tx in cursor:
        await pg_conn.execute('''
            INSERT INTO tenant_finance_tx (
                id, tenant_id, type, amount_minor, ref_id,
                note, fee_month, setup_fee_mode, created_by,
                balance_after_minor, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ON CONFLICT (tenant_id, ref_id) DO NOTHING
        ''',
            tx['id'],
            tx['tenant_id'],
            tx['type'],
            tx['amount_minor'],
            tx['ref_id'],
            tx.get('note'),
            tx.get('fee_month'),
            tx.get('setup_fee_mode'),
            tx.get('created_by'),
            tx.get('balance_after_minor'),
            tx.get('created_at'),
        )
```

## Running Migrations

```bash
# Generate new migration
alembic revision --autogenerate -m "description"

# Run all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history
```

## Locking Strategy Notes

For PostgreSQL, use `SELECT ... FOR UPDATE` when modifying buffer balance:

```sql
BEGIN;
  -- Lock the row
  SELECT buffer_balance_minor 
  FROM tenant_finance 
  WHERE tenant_id = 'xxx' 
  FOR UPDATE;
  
  -- Perform update
  UPDATE tenant_finance 
  SET buffer_balance_minor = buffer_balance_minor + 1000000,
      updated_at = NOW()
  WHERE tenant_id = 'xxx';
  
  -- Insert transaction log
  INSERT INTO tenant_finance_tx (...) VALUES (...);
COMMIT;
```

This prevents race conditions when multiple processes try to modify
the same tenant's buffer simultaneously.
