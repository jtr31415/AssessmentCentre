from app.security import (
    decrypt_secret,
    encrypt_secret,
    generate_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    h = hash_password("hunter2")
    assert h != "hunter2"
    assert verify_password("hunter2", h)
    assert not verify_password("wrong", h)


def test_secret_encrypt_roundtrip():
    secret = "sk-ant-abc123"
    token = encrypt_secret(secret)
    assert token != secret
    assert decrypt_secret(token) == secret


def test_generate_token_unique_and_long():
    a, b = generate_token(), generate_token()
    assert a != b
    assert len(a) >= 32
