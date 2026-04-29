import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass
from typing import Optional

from fastapi import Request

SESSION_KEY = "authenticated"
CSRF_COOKIE_NAME = "pm_csrf"


@dataclass
class SecuritySettings:
    deployment_mode: str
    auth_user: str
    auth_password: str
    auth_token: str
    secret_key: str
    secure_cookies: bool


def _load_settings() -> SecuritySettings:
    deployment_mode = os.getenv("PT_DEPLOYMENT_MODE", "internet").strip().lower()
    # Seguridad por defecto: cookies solo por HTTPS.
    # Para desarrollo local en http://localhost usar PT_SECURE_COOKIES=false
    secure_cookies = os.getenv("PT_SECURE_COOKIES", "true").strip().lower() == "true"

    secret_key = os.getenv("PT_SECRET_KEY") or secrets.token_urlsafe(48)
    auth_user = os.getenv("PT_AUTH_USER", "admin")
    auth_password = os.getenv("PT_AUTH_PASSWORD") or secrets.token_urlsafe(24)
    auth_token = os.getenv("PT_AUTH_TOKEN", "")

    return SecuritySettings(
        deployment_mode=deployment_mode,
        auth_user=auth_user,
        auth_password=auth_password,
        auth_token=auth_token,
        secret_key=secret_key,
        secure_cookies=secure_cookies,
    )


SETTINGS = _load_settings()


def is_html_request(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return "text/html" in accept or request.headers.get("hx-request") == "true"


def should_require_auth(path: str, method: str) -> bool:
    if path.startswith("/projects"):
        return True
    if path.startswith("/users"):
        return True
    if path.startswith("/projects/") and "/decisions" in path:
        return True
    if path.startswith("/partials/") and method.upper() not in {"GET", "HEAD", "OPTIONS"}:
        return True
    return False


def is_authenticated(request: Request) -> bool:
    if request.session.get(SESSION_KEY):
        return True

    auth_header = request.headers.get("authorization", "")
    if SETTINGS.auth_token and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        if hmac.compare_digest(token, SETTINGS.auth_token):
            return True

    api_token = request.headers.get("x-api-token", "")
    if SETTINGS.auth_token and api_token and hmac.compare_digest(api_token, SETTINGS.auth_token):
        return True

    return False


def check_login_credentials(username: str, password: str) -> bool:
    return hmac.compare_digest(username or "", SETTINGS.auth_user) and hmac.compare_digest(
        password or "", SETTINGS.auth_password
    )


def issue_csrf_token(request: Request) -> str:
    token = request.cookies.get(CSRF_COOKIE_NAME)
    if token:
        return token
    seed = secrets.token_urlsafe(32)
    digest = hmac.new(SETTINGS.secret_key.encode("utf-8"), seed.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{seed}.{digest}"


def validate_csrf(request: Request, provided_token: Optional[str]) -> bool:
    expected = request.cookies.get(CSRF_COOKIE_NAME, "")
    if not expected or not provided_token:
        return False
    return hmac.compare_digest(expected, provided_token)


def csrf_token(request: Request) -> str:
    return request.cookies.get(CSRF_COOKIE_NAME, "")
