import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt


_PASSWORD_HASH_ITERATIONS = 310_000


def _jwt_secret() -> str:
	secret = os.getenv("JWT_SECRET_KEY")
	if not secret:
		raise RuntimeError("JWT_SECRET_KEY is not set")
	if len(secret) < 32:
		raise RuntimeError("JWT_SECRET_KEY must contain at least 32 characters")
	return secret


def create_access_token(user_id: int) -> str:
	expires_at = datetime.now(timezone.utc) + timedelta(
		minutes=int(os.getenv("JWT_ACCESS_TOKEN_MINUTES", "60"))
	)
	return jwt.encode(
		{"sub": str(user_id), "exp": expires_at},
		_jwt_secret(),
		algorithm="HS256",
	)


def create_password_reset_token(user_id: int, password_hash: str) -> str:
	expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
	password_version = hmac.new(
		_jwt_secret().encode("utf-8"), password_hash.encode("utf-8"), hashlib.sha256
	).hexdigest()
	return jwt.encode(
		{
			"sub": str(user_id),
			"purpose": "password_reset",
			"password_version": password_version,
			"exp": expires_at,
		},
		_jwt_secret(),
		algorithm="HS256",
	)


def get_user_id_from_password_reset_token(
	token: str, current_password_hash: str | None = None
) -> int | None:
	try:
		payload = jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
		if payload.get("purpose") != "password_reset":
			return None
		if current_password_hash is not None:
			password_version = hmac.new(
				_jwt_secret().encode("utf-8"),
				current_password_hash.encode("utf-8"),
				hashlib.sha256,
			).hexdigest()
			if not hmac.compare_digest(payload["password_version"], password_version):
				return None
		return int(payload["sub"])
	except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
		return None


def get_user_id_from_token(token: str) -> int | None:
	try:
		payload = jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
		if payload.get("purpose") == "password_reset":
			return None
		return int(payload["sub"])
	except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
		return None


def hash_password(password: str) -> str:
	salt = secrets.token_bytes(16)
	password_hash = hashlib.pbkdf2_hmac(
		"sha256", password.encode("utf-8"), salt, _PASSWORD_HASH_ITERATIONS
	)
	return f"pbkdf2_sha256${_PASSWORD_HASH_ITERATIONS}${salt.hex()}${password_hash.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
	try:
		algorithm, iterations, salt_hex, expected_hash = stored_hash.split("$")
		if algorithm != "pbkdf2_sha256":
			return False
		candidate_hash = hashlib.pbkdf2_hmac(
			"sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
		).hex()
	except (ValueError, TypeError):
		return False
	return hmac.compare_digest(candidate_hash, expected_hash)
