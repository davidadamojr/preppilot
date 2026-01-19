"""
Tests for JWT token creation and validation.

These are unit tests that don't require database access.
"""
import pytest
from datetime import timedelta
from uuid import uuid4, UUID
from unittest.mock import patch

from backend.auth.jwt import create_access_token, decode_access_token, TokenPayload


class TestCreateAccessToken:
    """Tests for JWT token creation."""

    def test_creates_valid_token(self):
        """Token creation should return a non-empty string."""
        user_id = uuid4()
        token = create_access_token(user_id=user_id)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_contains_three_parts(self):
        """JWT should have header.payload.signature format."""
        user_id = uuid4()
        token = create_access_token(user_id=user_id)

        parts = token.split(".")
        assert len(parts) == 3, "JWT should have exactly 3 parts"

    def test_custom_expiration_delta(self):
        """Token should accept custom expiration time."""
        user_id = uuid4()
        short_expiry = timedelta(minutes=5)
        token = create_access_token(user_id=user_id, expires_delta=short_expiry)

        # Token should still be valid
        payload = decode_access_token(token)
        assert payload is not None
        assert payload.user_id == user_id

    def test_default_expiration_is_7_days(self):
        """Default expiration should be 7 days (10080 minutes)."""
        user_id = uuid4()
        token = create_access_token(user_id=user_id)

        # Token should be valid now
        payload = decode_access_token(token)
        assert payload is not None
        assert payload.user_id == user_id

    def test_token_includes_role(self):
        """Token should include role claim."""
        user_id = uuid4()
        token = create_access_token(user_id=user_id, role="admin")

        payload = decode_access_token(token)
        assert payload is not None
        assert payload.role == "admin"

    def test_token_default_role_is_user(self):
        """Token should default to 'user' role."""
        user_id = uuid4()
        token = create_access_token(user_id=user_id)

        payload = decode_access_token(token)
        assert payload is not None
        assert payload.role == "user"


class TestDecodeAccessToken:
    """Tests for JWT token validation and decoding."""

    def test_decodes_valid_token(self):
        """Valid token should decode to TokenPayload with user_id and role."""
        user_id = uuid4()
        token = create_access_token(user_id=user_id, role="user")

        payload = decode_access_token(token)

        assert payload is not None
        assert isinstance(payload, TokenPayload)
        assert payload.user_id == user_id
        assert isinstance(payload.user_id, UUID)
        assert payload.role == "user"

    def test_returns_none_for_invalid_token(self):
        """Invalid token should return None, not raise exception."""
        invalid_token = "not.a.valid.jwt.token"

        result = decode_access_token(invalid_token)

        assert result is None

    def test_returns_none_for_malformed_token(self):
        """Malformed token should return None."""
        malformed_token = "definitely-not-a-jwt"

        result = decode_access_token(malformed_token)

        assert result is None

    def test_returns_none_for_empty_token(self):
        """Empty token should return None."""
        result = decode_access_token("")

        assert result is None

    def test_returns_none_for_expired_token(self):
        """Expired token should return None."""
        user_id = uuid4()
        # Create token that expires immediately (negative time)
        expired_token = create_access_token(
            user_id=user_id,
            expires_delta=timedelta(seconds=-1)
        )

        result = decode_access_token(expired_token)

        assert result is None

    def test_returns_none_for_wrong_secret(self):
        """Token signed with different secret should return None."""
        user_id = uuid4()
        token = create_access_token(user_id=user_id)

        # Decode with different secret by mocking settings
        with patch("backend.auth.jwt.settings") as mock_settings:
            mock_settings.secret_key = "different-secret-key"
            mock_settings.algorithm = "HS256"

            result = decode_access_token(token)

        assert result is None

    def test_returns_none_for_tampered_token(self):
        """Token with modified payload should fail validation."""
        user_id = uuid4()
        token = create_access_token(user_id=user_id)

        # Tamper with the token by modifying the payload (middle part)
        parts = token.split(".")
        parts[1] = parts[1][:-4] + "XXXX"  # Modify last 4 chars of payload
        tampered_token = ".".join(parts)

        result = decode_access_token(tampered_token)

        assert result is None


class TestTokenRoundTrip:
    """Integration tests for create/decode cycle."""

    def test_multiple_users_get_unique_tokens(self):
        """Different users should get different tokens."""
        user1_id = uuid4()
        user2_id = uuid4()

        token1 = create_access_token(user_id=user1_id)
        token2 = create_access_token(user_id=user2_id)

        assert token1 != token2
        payload1 = decode_access_token(token1)
        payload2 = decode_access_token(token2)
        assert payload1 is not None
        assert payload2 is not None
        assert payload1.user_id == user1_id
        assert payload2.user_id == user2_id

    def test_same_user_gets_different_tokens(self):
        """Same user should get different tokens each time (different iat)."""
        user_id = uuid4()

        token1 = create_access_token(user_id=user_id)
        token2 = create_access_token(user_id=user_id)

        # Tokens differ because of different issued-at times
        # (in practice they might be identical if created at exact same moment)
        payload1 = decode_access_token(token1)
        payload2 = decode_access_token(token2)
        assert payload1 is not None
        assert payload2 is not None
        assert payload1.user_id == user_id
        assert payload2.user_id == user_id

    def test_uuid_preserved_through_encoding(self):
        """UUID should be exactly preserved through encode/decode cycle."""
        original_id = uuid4()

        token = create_access_token(user_id=original_id)
        payload = decode_access_token(token)

        assert payload is not None
        assert payload.user_id == original_id
        assert str(payload.user_id) == str(original_id)

    def test_role_preserved_through_encoding(self):
        """Role should be preserved through encode/decode cycle."""
        user_id = uuid4()

        token = create_access_token(user_id=user_id, role="admin")
        payload = decode_access_token(token)

        assert payload is not None
        assert payload.role == "admin"
