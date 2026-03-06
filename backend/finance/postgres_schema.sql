-- ============================================================================
-- LooxGame Tenant Finance - PostgreSQL Schema
-- Target: AWS RDS PostgreSQL
-- ============================================================================

-- Tenant Finance Table (Buffer/Escrow Management)
CREATE TABLE IF NOT EXISTS tenant_finance (
    tenant_id VARCHAR(36) PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
    
    -- Buffer/Escrow Balance (stored as integer minor units - IDR)
    buffer_balance_minor BIGINT NOT NULL DEFAULT 0,
    buffer_min_threshold_minor BIGINT NOT NULL DEFAULT 25000000, -- 25M IDR
    
    -- Freeze status
    is_frozen BOOLEAN NOT NULL DEFAULT TRUE,
    frozen_reason VARCHAR(500),
    frozen_at TIMESTAMP WITH TIME ZONE,
    
    -- Commercial terms
    ggr_share_percent REAL NOT NULL DEFAULT 15.0,
    infra_fee_monthly_minor BIGINT NOT NULL DEFAULT 5000000, -- 5M IDR
    setup_fee_minor BIGINT NOT NULL DEFAULT 25000000, -- 25M IDR
    setup_fee_mode VARCHAR(20) NOT NULL DEFAULT 'ACTIVATION_DEPOSIT' 
        CHECK (setup_fee_mode IN ('ACTIVATION_DEPOSIT', 'NON_REFUNDABLE')),
    setup_fee_paid BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for tenant_finance
CREATE INDEX IF NOT EXISTS idx_tenant_finance_frozen 
    ON tenant_finance(is_frozen) WHERE is_frozen = TRUE;

-- Trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_tenant_finance_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_tenant_finance_updated_at
    BEFORE UPDATE ON tenant_finance
    FOR EACH ROW
    EXECUTE FUNCTION update_tenant_finance_updated_at();


-- Tenant Finance Transactions Table (Transaction Log)
CREATE TABLE IF NOT EXISTS tenant_finance_tx (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenant_finance(tenant_id) ON DELETE CASCADE,
    
    -- Transaction type
    type VARCHAR(20) NOT NULL CHECK (type IN (
        'TOPUP', 'ADJUST', 'SETTLEMENT_DEDUCT', 'INFRA_FEE', 'SETUP_FEE'
    )),
    
    -- Amount (positive for credits, negative for debits)
    amount_minor BIGINT NOT NULL,
    
    -- Idempotency key - MUST be unique per tenant
    ref_id VARCHAR(100) NOT NULL,
    
    -- Additional fields
    note VARCHAR(500),
    fee_month VARCHAR(7), -- YYYY-MM for monthly fees
    setup_fee_mode VARCHAR(20),
    created_by VARCHAR(36),
    
    -- Balance snapshot after this transaction
    balance_after_minor BIGINT,
    
    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Idempotency constraint
    CONSTRAINT uq_tenant_finance_tx_ref_id UNIQUE (tenant_id, ref_id)
);

-- Indexes for tenant_finance_tx
CREATE INDEX IF NOT EXISTS idx_tenant_finance_tx_tenant_created 
    ON tenant_finance_tx(tenant_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_tenant_finance_tx_type 
    ON tenant_finance_tx(type);


-- ============================================================================
-- LOCKING STRATEGY FOR POSTGRES
-- ============================================================================
-- 
-- For atomic buffer operations (topup, charge fees), use SELECT ... FOR UPDATE
-- to prevent race conditions:
--
-- BEGIN;
--   SELECT buffer_balance_minor FROM tenant_finance 
--   WHERE tenant_id = $1 FOR UPDATE;
--   
--   UPDATE tenant_finance 
--   SET buffer_balance_minor = buffer_balance_minor + $2,
--       updated_at = NOW()
--   WHERE tenant_id = $1;
--   
--   INSERT INTO tenant_finance_tx (id, tenant_id, type, amount_minor, ref_id, ...)
--   VALUES (...);
-- COMMIT;
--
-- This ensures:
-- 1. Row-level lock prevents concurrent modifications
-- 2. Atomic increment/decrement
-- 3. Consistent balance_after_minor snapshots
--
-- ============================================================================


-- ============================================================================
-- SAMPLE QUERIES
-- ============================================================================

-- Check if tenant can operate (for enforcement)
-- SELECT 
--     tenant_id,
--     buffer_balance_minor,
--     buffer_min_threshold_minor,
--     is_frozen,
--     CASE 
--         WHEN is_frozen OR buffer_balance_minor < buffer_min_threshold_minor 
--         THEN FALSE 
--         ELSE TRUE 
--     END as can_operate,
--     GREATEST(0, buffer_min_threshold_minor - buffer_balance_minor) as required_topup_minor
-- FROM tenant_finance
-- WHERE tenant_id = $1;

-- Get recent transactions
-- SELECT * FROM tenant_finance_tx 
-- WHERE tenant_id = $1 
-- ORDER BY created_at DESC 
-- LIMIT 50;

-- Monthly infra fee report (for super_admin)
-- SELECT 
--     tf.tenant_id,
--     t.name as tenant_name,
--     tf.buffer_balance_minor,
--     tf.infra_fee_monthly_minor,
--     (SELECT created_at FROM tenant_finance_tx 
--      WHERE tenant_id = tf.tenant_id AND type = 'INFRA_FEE' AND fee_month = '2025-07'
--      LIMIT 1) as infra_fee_charged_at
-- FROM tenant_finance tf
-- JOIN tenants t ON t.id = tf.tenant_id;
