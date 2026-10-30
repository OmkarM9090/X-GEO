"""Password hashing, bearer parsing, JWT handling and misc helpers."""

from __future__ import annotations

import time

import jwt as pyjwt
import pytest

from app.config import get_settings
from app.core.exceptions import InvalidInputError, UnauthorizedError
from app.core.security import (
    constant_time_compare,
    create_local_token,
    decode_jwt,
    extract_bearer_token,
    generate_request_id,
    hash_ip,
    hash_password,
    password_needs_rehash,
    redact_url,
    token_fingerprint,
    verify_password,
)
from tests.conftest import TEST_JWT_SECRET


class TestPasswordHashing:
    def test_round_trip(self) -> None:
        encoded = hash_password("correct horse battery staple")
        assert verify_password("correct horse battery staple", encoded) is True

    def test_wrong_password_rejected(self) -> None:
        encoded = hash_password("correct horse battery staple")
        assert verify_password("wrong password", encoded) is False

    def test_hashes_are_unique_per_call(self) -> None:
        assert hash_password("same-password") != hash_password("same-password")

    def test_format_is_self_describing(self) -> None:
        encoded = hash_password("correct horse battery staple")
        algorithm, cost, salt, digest = encoded.split("$", 3)
        assert algorithm == "scrypt"
        assert int(cost) >= 2**14
        assert salt and digest

    def test_short_passwords_rejected(self) -> None:
        with pytest.raises(InvalidInputError, match="at least"):
            hash_password("short")

    def test_malformed_hash_returns_false(self) -> None:
        assert verify_password("whatever", "not-a-hash") is False
        assert verify_password("whatever", "") is False
        assert verify_password("whatever", "scrypt$broken") is False

    def test_needs_rehash_for_unknown_format(self) -> None:
        assert password_needs_rehash("plaintext:secret") is True
        assert password_needs_rehash(hash_password("correct horse battery staple")) is False


class TestBearerTokens:
    def test_extracts_token(self) -> None:
        assert extract_bearer_token("Bearer abc.def.ghi") == "abc.def.ghi"

    def test_scheme_is_case_insensitive(self) -> None:
        assert extract_bearer_token("bearer abc") == "abc"

    @pytest.mark.parametrize("header", [None, "", "Basic abc", "Bearer", "Bearer   "])
    def test_invalid_headers_rejected(self, header: str | None) -> None:
        with pytest.raises(UnauthorizedError):
            extract_bearer_token(header)


class TestJwtHandling:
    def test_decodes_locally_signed_token(self) -> None:
        token = create_local_token(subject="user-123", email="dev@example.com")
        claims = decode_jwt(token)
        assert claims.subject == "user-123"
        assert claims.email == "dev@example.com"
        assert claims.role == "authenticated"
        assert claims.audience == get_settings().SUPABASE_JWT_AUDIENCE
        assert claims.expires_at is not None

    def test_rejects_token_signed_with_another_secret(self) -> None:
        settings = get_settings()
        forged = pyjwt.encode(
            {
                "sub": "attacker",
                "aud": settings.SUPABASE_JWT_AUDIENCE,
                "exp": int(time.time()) + 600,
            },
            "a-completely-different-secret-value",
            algorithm="HS256",
        )
        with pytest.raises(UnauthorizedError, match="Invalid authentication token"):
            decode_jwt(forged)

    def test_rejects_expired_token(self) -> None:
        expired = create_local_token(subject="user-123", ttl_seconds=-10)
        with pytest.raises(UnauthorizedError, match="expired"):
            decode_jwt(expired)

    def test_rejects_wrong_audience(self) -> None:
        wrong_audience = create_local_token(subject="user-123", audience="some-other-service")
        with pytest.raises(UnauthorizedError):
            decode_jwt(wrong_audience)

    def test_rejects_alg_none(self) -> None:
        unsigned = pyjwt.encode({"sub": "attacker"}, key=None, algorithm="none")
        with pytest.raises(UnauthorizedError):
            decode_jwt(unsigned)

    def test_rejects_missing_subject(self) -> None:
        settings = get_settings()
        token = pyjwt.encode(
            {
                "aud": settings.SUPABASE_JWT_AUDIENCE,
                "exp": int(time.time()) + 600,
                "iss": settings.auth_issuer or "x-geo-local",
            },
            TEST_JWT_SECRET,
            algorithm="HS256",
        )
        with pytest.raises(UnauthorizedError):
            decode_jwt(token)

    def test_token_fingerprint_is_stable_and_short(self) -> None:
        fingerprint = token_fingerprint("some.jwt.token")
        assert fingerprint == token_fingerprint("some.jwt.token")
        assert fingerprint != token_fingerprint("some.jwt.other")
        assert len(fingerprint) <= 32

    def test_token_fingerprint_does_not_leak_the_token(self) -> None:
        token = create_local_token(subject="user-123")
        assert token not in token_fingerprint(token)


class TestMiscHelpers:
    def test_constant_time_compare(self) -> None:
        assert constant_time_compare("abc", "abc") is True
        assert constant_time_compare("abc", "abd") is False
        assert constant_time_compare("abc", "abcd") is False

    def test_redact_url_hides_credentials(self) -> None:
        redacted = redact_url("https://user:secret@example.com/private?token=abc")
        assert "secret" not in redacted
        assert "example.com" in redacted

    def test_redact_url_keeps_plain_urls_readable(self) -> None:
        assert redact_url("https://example.com/pricing") == "https://example.com/pricing"

    def test_request_ids_are_unique_and_prefixed(self) -> None:
        first, second = generate_request_id(), generate_request_id()
        assert first != second
        assert len(first) >= 16

    def test_hash_ip_is_stable_and_irreversible(self) -> None:
        """IP hashes must be stable for rate limiting but not reversible."""
        digest = hash_ip("203.0.113.7")
        assert digest == hash_ip("203.0.113.7")
        assert "203.0.113.7" not in digest
        assert digest != hash_ip("203.0.113.8")
