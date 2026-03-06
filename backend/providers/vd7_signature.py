"""VD7 Aggregator - HMAC-SHA256 Signature Module.

Implements the Sign Hashing Process as per VD7 documentation:
1. Sort params alphabetically by key (exclude 'sign')
2. URL-encode and flatten to query string
3. HMAC-SHA256 with agent_secret

Special rules:
- GetBalance & gameReward: NO transaction_id in signature
- Batch APIs: sort transaction_ids ascending, join with '.'
"""

import hmac
import hashlib
from typing import Any, Optional
from urllib.parse import quote
import logging

logger = logging.getLogger(__name__)

# Endpoints that exclude transaction_id from signature
NO_TRANSACTION_ID_ENDPOINTS = frozenset(["getBalance", "gameReward"])

# Batch endpoints that require special transaction_id handling
BATCH_ENDPOINTS = frozenset(["debitBatch", "creditBatch", "cancelBetBatch", "tipBatch", "cancelTipBatch"])


def is_empty_value(value: Any) -> bool:
    """Check if value should be excluded from signature."""
    if value is None:
        return True
    if isinstance(value, str) and len(value) == 0:
        return True
    if isinstance(value, dict) and len(value) == 0:
        return True
    return False


def flatten_map(
    data: dict[str, Any],
    exclude: Optional[set[str]] = None,
    prefix: str = ""
) -> str:
    """Flatten nested dict to URL-encoded query string.
    
    Args:
        data: Dictionary to flatten
        exclude: Set of keys to exclude (e.g., {'sign'})
        prefix: Prefix for nested keys (internal use)
        
    Returns:
        URL-encoded query string like 'agent_code=demo&amount=100'
    """
    if data is None:
        return ""
    
    exclude = exclude or set()
    parts = []
    
    # Sort keys alphabetically
    for key in sorted(data.keys()):
        if key in exclude:
            continue
        
        value = data[key]
        if is_empty_value(value):
            continue
        
        full_key = f"{prefix}.{key}" if prefix else key
        escaped_key = quote(full_key, safe='')
        
        if isinstance(value, dict):
            # Recursively flatten nested dict
            sub_parts = flatten_map(value, exclude, full_key)
            if sub_parts:
                parts.append(sub_parts)
        elif isinstance(value, list):
            # Handle arrays - flatten each item with index
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    item_prefix = f"{full_key}[{i}]"
                    sub_parts = flatten_map(item, exclude, item_prefix)
                    if sub_parts:
                        parts.append(sub_parts)
                else:
                    item_key = f"{escaped_key}[{i}]"
                    parts.append(f"{item_key}={quote(str(item), safe='')}")
        else:
            # Simple value
            parts.append(f"{escaped_key}={quote(str(value), safe='')}")
    
    return "&".join(parts)


def prepare_batch_transaction_id(transactions: list[dict]) -> str:
    """Prepare transaction_id for batch operations.
    
    Sort all transaction_ids ascending and join with '.'
    
    Args:
        transactions: List of transaction dicts with 'transaction_id'
        
    Returns:
        Joined string like 'tx1.tx2.tx3'
    """
    tx_ids = []
    for tx in transactions:
        tx_id = tx.get("transaction_id")
        if tx_id:
            tx_ids.append(str(tx_id))
    
    tx_ids.sort()
    return ".".join(tx_ids)


def generate_sign(
    data: dict[str, Any],
    secret: str,
    endpoint: Optional[str] = None,
) -> str:
    """Generate HMAC-SHA256 signature for VD7 API request.
    
    Args:
        data: Request data dictionary
        secret: Agent secret key for HMAC
        endpoint: Endpoint name for special handling rules
        
    Returns:
        Hex-encoded HMAC-SHA256 signature
    """
    # Create working copy
    sign_data = data.copy()
    
    # Handle special rules based on endpoint
    if endpoint:
        endpoint_lower = endpoint.lower()
        
        # GetBalance & gameReward: exclude transaction_id
        if endpoint_lower in {e.lower() for e in NO_TRANSACTION_ID_ENDPOINTS}:
            sign_data.pop("transaction_id", None)
        
        # Batch endpoints: join transaction_ids with '.'
        if endpoint_lower in {e.lower() for e in BATCH_ENDPOINTS}:
            transactions = sign_data.get("transactions", [])
            if transactions:
                batch_tx_id = prepare_batch_transaction_id(transactions)
                sign_data["transaction_id"] = batch_tx_id
    
    # Flatten to query string (exclude 'sign' field)
    flattened = flatten_map(sign_data, exclude={"sign"})
    
    # Compute HMAC-SHA256
    h = hmac.new(
        key=secret.encode("utf-8"),
        msg=flattened.encode("utf-8"),
        digestmod=hashlib.sha256
    )
    
    signature = h.hexdigest()
    logger.debug(f"VD7 sign generated: data_flat={flattened[:100]}..., sign={signature[:16]}...")
    
    return signature


def verify_sign(
    data: dict[str, Any],
    secret: str,
    expected_sign: str,
    endpoint: Optional[str] = None,
) -> bool:
    """Verify HMAC-SHA256 signature from VD7 callback.
    
    Args:
        data: Request data dictionary (including 'sign')
        secret: Agent secret key for HMAC
        expected_sign: The 'sign' value from request
        endpoint: Endpoint name for special handling rules
        
    Returns:
        True if signature is valid
    """
    generated = generate_sign(data, secret, endpoint)
    
    # Constant-time comparison to prevent timing attacks
    is_valid = hmac.compare_digest(generated, expected_sign)
    
    if not is_valid:
        logger.warning(f"VD7 signature mismatch: expected={expected_sign[:16]}..., got={generated[:16]}...")
    
    return is_valid


# ============ UNIT TESTS ============
if __name__ == "__main__":
    import json
    
    print("=" * 60)
    print("VD7 Signature Module - Unit Tests")
    print("=" * 60)
    
    test_secret = "demo-secret-key"
    
    # Test 1: Basic signature generation
    print("\n[Test 1] Basic signature generation")
    basic_data = {
        "agent_code": "demoagent",
        "type": "credit",
        "currency_code": "TRY",
    }
    sign1 = generate_sign(basic_data, test_secret)
    print(f"Data: {json.dumps(basic_data)}")
    print(f"Signature: {sign1}")
    assert len(sign1) == 64, "Signature should be 64 hex chars"
    print("✅ PASS")
    
    # Test 2: Verify signature
    print("\n[Test 2] Verify signature")
    is_valid = verify_sign(basic_data, test_secret, sign1)
    assert is_valid, "Signature should be valid"
    print("✅ PASS")
    
    # Test 3: Invalid signature detection
    print("\n[Test 3] Invalid signature detection")
    is_invalid = verify_sign(basic_data, test_secret, "wrong_signature")
    assert not is_invalid, "Wrong signature should be rejected"
    print("✅ PASS")
    
    # Test 4: GetBalance - NO transaction_id
    print("\n[Test 4] GetBalance - exclude transaction_id")
    getbalance_data = {
        "username": "player1",
        "agent_code": "EGS",
        "currency_code": "IDR",
        "transaction_id": "should_be_excluded",
        "action_id": "123",
    }
    sign_with_txid = generate_sign(getbalance_data, test_secret)
    sign_getbalance = generate_sign(getbalance_data, test_secret, endpoint="getBalance")
    # Signatures should be different because getBalance excludes transaction_id
    assert sign_with_txid != sign_getbalance, "GetBalance should exclude transaction_id"
    print(f"With transaction_id: {sign_with_txid[:32]}...")
    print(f"GetBalance (excluded): {sign_getbalance[:32]}...")
    print("✅ PASS")
    
    # Test 5: gameReward - NO transaction_id
    print("\n[Test 5] gameReward - exclude transaction_id")
    reward_data = {
        "username": "player1",
        "agent_code": "EGS",
        "transaction_id": "should_be_excluded",
        "action_id": "456",
    }
    sign_gamereward = generate_sign(reward_data, test_secret, endpoint="gameReward")
    sign_normal = generate_sign(reward_data, test_secret)
    assert sign_gamereward != sign_normal, "gameReward should exclude transaction_id"
    print("✅ PASS")
    
    # Test 6: Batch transaction_id handling
    print("\n[Test 6] Batch transaction_id (sorted + joined with '.')")
    batch_data = {
        "provider_code": "LLG",
        "action_id": "batch123",
        "transactions": [
            {"transaction_id": "tx_c", "amount": 100},
            {"transaction_id": "tx_a", "amount": 200},
            {"transaction_id": "tx_b", "amount": 150},
        ]
    }
    batch_tx_id = prepare_batch_transaction_id(batch_data["transactions"])
    assert batch_tx_id == "tx_a.tx_b.tx_c", f"Expected 'tx_a.tx_b.tx_c', got '{batch_tx_id}'"
    print(f"Batch transaction_id: {batch_tx_id}")
    sign_batch = generate_sign(batch_data, test_secret, endpoint="cancelBetBatch")
    print(f"Batch signature: {sign_batch}")
    print("✅ PASS")
    
    # Test 7: Alphabetical sorting
    print("\n[Test 7] Alphabetical key sorting")
    unsorted_data = {
        "zebra": "last",
        "apple": "first",
        "mango": "middle",
    }
    flattened = flatten_map(unsorted_data)
    expected_order = "apple=first&mango=middle&zebra=last"
    assert flattened == expected_order, f"Expected '{expected_order}', got '{flattened}'"
    print(f"Flattened: {flattened}")
    print("✅ PASS")
    
    # Test 8: Empty value exclusion
    print("\n[Test 8] Empty value exclusion")
    data_with_empty = {
        "valid": "value",
        "empty_string": "",
        "none_value": None,
        "empty_dict": {},
    }
    flattened_clean = flatten_map(data_with_empty)
    assert "empty_string" not in flattened_clean, "Empty string should be excluded"
    assert "none_value" not in flattened_clean, "None should be excluded"
    assert "empty_dict" not in flattened_clean, "Empty dict should be excluded"
    print(f"Flattened (empty excluded): {flattened_clean}")
    print("✅ PASS")
    
    # Test 9: URL encoding special chars
    print("\n[Test 9] URL encoding special characters")
    special_data = {
        "name": "test player",
        "symbol": "$100",
    }
    flattened_encoded = flatten_map(special_data)
    assert "%20" in flattened_encoded or "+" in flattened_encoded or "test%20player" in flattened_encoded, "Space should be encoded"
    assert "%24" in flattened_encoded, "$ should be encoded"
    print(f"Encoded: {flattened_encoded}")
    print("✅ PASS")
    
    # Test 10: Deterministic signatures
    print("\n[Test 10] Deterministic signatures (same input = same output)")
    sign_a = generate_sign(basic_data, test_secret)
    sign_b = generate_sign(basic_data, test_secret)
    assert sign_a == sign_b, "Same input should produce same signature"
    print("✅ PASS")
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED! ✅")
    print("=" * 60)
