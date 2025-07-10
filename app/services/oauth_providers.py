"""OAuth provider abstraction for Google and GitHub.

This module defines a common interface for OAuth providers and concrete
implementations for Google and GitHub. It handles PKCE, state generation, token
exchange, and user-info retrieval to keep the rest of the codebase DRY and
maintainable.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple

import httpx
from pydantic import BaseModel, Field

from app.config import get_settings

settings = get_settings()


def _generate_pkce_pair() -> Tuple[str, str]:
    """Generate code_verifier and code_challenge values for PKCE."""
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    return verifier, challenge


class OAuthState(BaseModel):
    """Structured state payload stored in signed cookie/token."""

    csrf_token: str = Field(..., alias="csrf")
    next_url: Optional[str] = None  # Where to redirect after login
    provider: str

    class Config:
        allow_population_by_field_name = True


class OAuthUserInfo(BaseModel):
    """Normalized user info returned to the caller of provider abstraction."""

    sub: str
    email: str
    email_verified: bool = True
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None


class OAuthProvider(ABC):
    """Abstract base class encapsulating provider-specific details."""

    name: str  # pylint: disable=invalid-name

    def __init__(self) -> None:
        self.client = httpx.AsyncClient(timeout=5)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    @abstractmethod
    async def get_authorization_url(
        self, *, state: str, code_challenge: str
    ) -> str:
        """Return the full authorization URL for redirect."""

    @abstractmethod
    async def exchange_code_for_token(
        self, *, code: str, code_verifier: str, redirect_uri: str
    ) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""

    @abstractmethod
    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """Fetch user profile and return normalized info."""

    # ------------------------------------------------------------------
    # Convenience factory
    # ------------------------------------------------------------------
    @classmethod
    def factory(cls, provider: str) -> "OAuthProvider":
        provider = provider.lower()
        if provider == "google":
            return GoogleOAuthProvider()
        if provider == "github":
            return GitHubOAuthProvider()
        raise ValueError(f"Unsupported provider: {provider}")


# ------------------------------------------------------------
# Concrete provider implementations
# ------------------------------------------------------------


class GoogleOAuthProvider(OAuthProvider):
    name = "google"

    AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
    USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"

    async def get_authorization_url(
        self, *, state: str, code_challenge: str
    ) -> str:  # noqa: D401
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "response_type": "code",
            "scope": "openid email profile",
            "redirect_uri": self._redirect_uri,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "prompt": "select_account",
        }
        query = str(httpx.QueryParams(params))
        return f"{self.AUTH_ENDPOINT}?{query}"

    async def exchange_code_for_token(
        self, *, code: str, code_verifier: str, redirect_uri: str
    ) -> Dict[str, Any]:  # noqa: D401
        data = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "code": code,
            "code_verifier": code_verifier,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
        print("Google token exchange payload:", data)
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(self.TOKEN_ENDPOINT, data=data,
                                     headers={"Content-Type": "application/x-www-form-urlencoded"})
            if resp.status_code >= 400:
                print("Google token exchange error", resp.status_code, resp.text)
            resp.raise_for_status()
            return resp.json()

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:  # noqa: D401
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                self.USERINFO_ENDPOINT,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            data = resp.json()

        return OAuthUserInfo(
            sub=data["sub"],
            email=data.get("email"),
            email_verified=data.get("email_verified", True),
            full_name=data.get("name"),
            avatar_url=data.get("picture"),
        )

    # Internal helpers
    @property
    def _redirect_uri(self) -> str:
        # Google should redirect to our backend API, not the frontend
        return f"{settings.BACKEND_BASE_URL}/api/v1/oauth/google/callback"


class GitHubOAuthProvider(OAuthProvider):
    name = "github"

    AUTH_ENDPOINT = "https://github.com/login/oauth/authorize"
    TOKEN_ENDPOINT = "https://github.com/login/oauth/access_token"
    USERINFO_ENDPOINT = "https://api.github.com/user"

    async def get_authorization_url(
        self, *, state: str, code_challenge: str
    ) -> str:  # noqa: D401
        params = {
            "client_id": settings.GITHUB_CLIENT_ID,
            "redirect_uri": self._redirect_uri,
            "state": state,
            "scope": "read:user user:email",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        query = str(httpx.QueryParams(params))
        return f"{self.AUTH_ENDPOINT}?{query}"

    async def exchange_code_for_token(
        self, *, code: str, code_verifier: str, redirect_uri: str
    ) -> Dict[str, Any]:  # noqa: D401
        headers = {"Accept": "application/json"}
        data = {
            "client_id": settings.GITHUB_CLIENT_ID,
            "client_secret": settings.GITHUB_CLIENT_SECRET,
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        }
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(self.TOKEN_ENDPOINT, data=data, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:  # noqa: D401
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(timeout=5) as client:
            user_resp = await client.get(self.USERINFO_ENDPOINT, headers=headers)
            user_resp.raise_for_status()
            user_data = user_resp.json()

            # Fetch primary email if not public
            email = user_data.get("email")
            if not email:
                emails_resp = await client.get(
                    "https://api.github.com/user/emails", headers=headers
                )
                emails_resp.raise_for_status()
                emails = emails_resp.json()
                primary_email = next(
                    (e for e in emails if e.get("primary") and e.get("verified")),
                    emails[0] if emails else None,
                )
                email = primary_email.get("email") if primary_email else None

        if not email:
            raise ValueError("Could not get email from GitHub")
            
        return OAuthUserInfo(
            sub=str(user_data["id"]),
            email=email,
            email_verified=True,  # GitHub verifies emails
            full_name=user_data.get("name"),
            avatar_url=user_data.get("avatar_url"),
        )

    @property
    def _redirect_uri(self) -> str:
        # GitHub should redirect to our backend API, not the frontend
        return f"{settings.BACKEND_BASE_URL}/api/v1/oauth/github/callback" 