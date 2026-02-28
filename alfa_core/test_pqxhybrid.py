import base64
import json

import pytest

from extra.pqxhybrid import (
    AlgorithmSpec,
    FrameFormatError,
    InvalidSignatureError,
    PQKeyPair,
    UnsupportedSchemeError,
    available_schemes,
    generate_keypair,
    register_provider,
    sign_frame,
    sign_message,
    unregister_provider,
    verify_frame,
    verify_message,
)


@pytest.mark.parametrize("scheme", ["falcon", "sphincs", "dilithium"])
def test_generate_keypair_deterministic(scheme: str) -> None:
    seed = b"seed-" + scheme.encode("ascii")
    pair1 = generate_keypair(scheme, seed=seed)
    pair2 = generate_keypair(scheme, seed=seed)
    assert pair1 == pair2


@pytest.mark.parametrize("scheme", ["falcon", "sphincs", "dilithium"])
def test_sign_and_verify_round_trip(scheme: str) -> None:
    pair = generate_keypair(scheme, seed=b"demo-seed-" + scheme.encode("ascii"))
    message = f"payload-{scheme}".encode("utf-8")
    signature = sign_message(message, pair)
    assert verify_message(message, signature, scheme, pair.public_key)


@pytest.mark.parametrize("scheme", ["falcon", "sphincs", "dilithium"])
def test_sign_frame_and_verify_round_trip(scheme: str) -> None:
    pair = generate_keypair(scheme, seed=b"frame-" + scheme.encode("ascii"))
    payload = f"frame-data-{scheme}".encode("utf-8")
    frame = sign_frame(payload, pair)
    decoded_payload, decoded_scheme = verify_frame(frame, pair.public_key)
    assert decoded_payload == payload
    assert decoded_scheme == scheme


def test_sign_frame_detects_tampering() -> None:
    pair = generate_keypair("falcon", seed=b"falcon-seed")
    frame = sign_frame(b"payload", pair)
    document = json.loads(frame)
    document["payload"] = base64.b64encode(b"evil").decode("ascii")
    tampered = json.dumps(document).encode("utf-8")
    with pytest.raises(InvalidSignatureError):
        verify_frame(tampered, pair.public_key)


def test_frame_format_error() -> None:
    pair = generate_keypair("sphincs", seed=b"format-seed")
    frame = sign_frame(b"payload", pair)
    broken = frame.replace(b"\"scheme\"", b"\"missing\"")
    with pytest.raises(FrameFormatError):
        verify_frame(broken, pair.public_key)


def test_sign_message_rejects_mismatched_keys() -> None:
    pair = generate_keypair("falcon", seed=b"a" * 16)
    wrong = PQKeyPair(scheme="falcon", public_key=pair.public_key, secret_key=b"0" * len(pair.secret_key))
    with pytest.raises(InvalidSignatureError):
        sign_message(b"payload", wrong)


def test_verify_message_with_wrong_scheme() -> None:
    pair = generate_keypair("falcon", seed=b"falcon")
    signature = sign_message(b"hello", pair)
    with pytest.raises(UnsupportedSchemeError):
        verify_message(b"hello", signature, scheme="unknown", public_key=pair.public_key)
def test_available_schemes_contains_placeholders() -> None:
    assert {"falcon", "sphincs", "dilithium"}.issubset(set(available_schemes()))


class _DemoProvider:
    def __init__(self, scheme: str = "demo") -> None:
        self.scheme = scheme
        self.spec = AlgorithmSpec(
            name=scheme,
            secret_size=8,
            public_size=8,
            signature_size=8,
            personalization=b"demo",
        )

    def generate_keypair(self, seed: bytes | None) -> PQKeyPair:
        if seed is None:
            seed = b"demo-seed"
        expanded = (seed * (self.spec.secret_size // len(seed) + 1))[: self.spec.secret_size]
        secret = expanded
        public = expanded[::-1]
        return PQKeyPair(self.scheme, public, secret)

    def sign(self, message: bytes, keypair: PQKeyPair) -> bytes:
        if keypair.scheme != self.scheme:
            raise InvalidSignatureError("Scheme mismatch for demo provider")
        digest = (keypair.public_key + message)[: self.spec.signature_size]
        return digest.ljust(self.spec.signature_size, b"\0")

    def verify(self, message: bytes, signature: bytes, public_key: bytes) -> bool:
        expected = (public_key + message)[: self.spec.signature_size].ljust(self.spec.signature_size, b"\0")
        return signature == expected


def test_register_custom_provider_round_trip() -> None:
    provider = _DemoProvider()
    register_provider(provider.scheme, provider)
    try:
        pair = generate_keypair(provider.scheme, seed=b"seed")
        signature = sign_message(b"payload", pair)
        assert verify_message(b"payload", signature, provider.scheme, pair.public_key)
    finally:
        unregister_provider(provider.scheme)


def test_register_provider_rejects_duplicates() -> None:
    provider = _DemoProvider("falcon")
    with pytest.raises(ValueError):
        register_provider("falcon", provider)


def test_unregister_provider_removes_scheme() -> None:
    provider = _DemoProvider("temp-scheme")
    register_provider(provider.scheme, provider)
    unregister_provider(provider.scheme)
    with pytest.raises(UnsupportedSchemeError):
        generate_keypair(provider.scheme)