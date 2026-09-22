from app.core.security import generate_api_key, hash_api_key, hash_password, mask_api_key, verify_password


def test_api_key_is_hashed_and_not_reversible():
    raw, digest, prefix = generate_api_key()
    assert raw.startswith("sk_stt_")
    assert digest == hash_api_key(raw)
    assert digest != raw
    assert prefix == raw[:16]
    assert mask_api_key(prefix).endswith("************")
    assert raw not in mask_api_key(prefix)


def test_password_hash_verifies():
    stored = hash_password("correct-password")
    assert verify_password(stored, "correct-password")
    assert not verify_password(stored, "wrong-password")
