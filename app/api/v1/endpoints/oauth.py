"""OAuth endpoints for social authentication (Google, GitHub).

These endpoints implement the OAuth initiation and callback logic using the
`OAuthProvider` abstraction so that each provider's specifics remain isolated.

Flow summary:
1. `/oauth/{provider}/initiate` – Generates state + PKCE, stores them in a
   signed cookie, and redirects user to provider auth screen.
2. `/oauth/{provider}/callback` – Validates state/PKCE, exchanges code for
   token, fetches user info, upserts user, issues our JWT tokens, and sets the
   refresh token cookie.
3. `/oauth/providers` – Returns list of supported providers + auth URL (so
   the frontend can dynamically render buttons if desired).
"""

from __future__ import annotations
import json
import secrets
from datetime import timedelta, datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic.json import pydantic_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dependencies import get_db, get_client_ip, get_user_agent
from app.models.user import User, UserRole
from app.services.oauth_providers import OAuthProvider, _generate_pkce_pair, OAuthUserInfo
from app.services.user_service import get_user_by_email, create_user
from app.services.session_service import create_user_session
from app.core.security import create_access_token, create_refresh_token
from app.models.session import SessionCreate

router = APIRouter(prefix="/oauth", tags=["oauth"])
settings = get_settings()

# Cookie names
STATE_COOKIE = "oauth_state"
VERIFIER_COOKIE = "oauth_verifier"
COOKIE_MAX_AGE_SECONDS = 1800  # 30 minutes


def _set_temp_cookie(response: Response, name: str, value: str) -> None:
    """Helper to set a short-lived secure cookie."""
    response.set_cookie(
        name,
        value,
        max_age=COOKIE_MAX_AGE_SECONDS,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        path="/api/v1/oauth",
    )


def _pop_temp_cookie(request: Request, name: str) -> str | None:
    """Retrieve cookie and clear it so it can't be replayed."""
    value = request.cookies.get(name)
    response: Response = request.state._response  # type: ignore[attr-defined]
    if value:
        response.delete_cookie(name, path="/api/v1/oauth")
    return value


@router.get("/providers", summary="List supported OAuth providers")
async def list_providers() -> Dict[str, str]:
    """Return supported providers and their initiation URLs."""
    providers = ["google", "github"]
    return {p: f"{settings.API_V1_STR}/oauth/{p}/initiate" for p in providers}


@router.get("/{provider}/initiate", summary="Initiate OAuth flow", status_code=307)
async def oauth_initiate(provider: str, request: Request) -> Response:
    provider = provider.lower()
    oauth_provider = OAuthProvider.factory(provider)

    # Generate state (CSRF token) and PKCE values
    csrf_token = secrets.token_urlsafe(16)
    code_verifier, code_challenge = _generate_pkce_pair()

    # Build redirect URL
    redirect_url = await oauth_provider.get_authorization_url(state=csrf_token, code_challenge=code_challenge)

    # Prepare redirect response
    response = RedirectResponse(redirect_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    # Store state and verifier in session/database for validation later
    # For now, we'll use a simple in-memory store (in production, use Redis or DB)
    if not hasattr(oauth_initiate, '_oauth_states'):
        oauth_initiate._oauth_states = {}
    
    oauth_initiate._oauth_states[csrf_token] = {
        'code_verifier': code_verifier,
        'provider': provider,
        'created_at': datetime.utcnow()
    }
    
    # Debug logging removed for production

    return response


@router.get("/{provider}/callback", summary="OAuth callback handler")
async def oauth_callback(
    provider: str,
    request: Request,
    response: Response,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Handle OAuth provider redirect and issue our tokens."""
    # Debug logging removed for production
    
    if error:
        raise HTTPException(status_code=400, detail=f"Provider error: {error}")

    # Validate state using in-memory storage
    if not state:
        raise HTTPException(status_code=400, detail="Missing state parameter")
    
    # Get stored state data
    oauth_states = getattr(oauth_initiate, '_oauth_states', {})
    stored_state_data = oauth_states.get(state)
    
    #

    if not stored_state_data:
        raise HTTPException(status_code=400, detail="Invalid or expired state parameter")
    
    # Check if state is not too old (30 minutes max)
    state_age = datetime.utcnow() - stored_state_data['created_at']
    if state_age.total_seconds() > 1800:  # 30 minutes
        # Clean up expired state
        del oauth_states[state]
        raise HTTPException(status_code=400, detail="State parameter expired")
    
    # Validate provider matches
    if stored_state_data['provider'] != provider:
        raise HTTPException(status_code=400, detail="Provider mismatch")

    # Get code_verifier from stored state
    code_verifier = stored_state_data['code_verifier']
    
    # Clean up used state
    del oauth_states[state]
    #

    if not code:
        raise HTTPException(status_code=400, detail="Authorization code missing")

    oauth_provider = OAuthProvider.factory(provider)
    redirect_uri = str(request.base_url).rstrip('/') + str(request.url.path)

    # Exchange code for access token
    token_data = await oauth_provider.exchange_code_for_token(
        code=code, code_verifier=code_verifier, redirect_uri=redirect_uri
    )
    access_token_provider = token_data.get("access_token")
    if not access_token_provider:
        raise HTTPException(status_code=400, detail="Failed to obtain provider token")

    # Fetch user info
    user_info: OAuthUserInfo = await oauth_provider.get_user_info(access_token_provider)
    if not user_info.email:
        raise HTTPException(status_code=400, detail="Provider did not return email")

    # Upsert user
    user = await get_user_by_email(db, user_info.email)
    if user is None:
        # Create user manually to support accounts without password (social login)
        user = User(
            email=user_info.email,
            username=user_info.email.split("@")[0],
            hashed_password=None,
            full_name=user_info.full_name,
            is_verified=user_info.email_verified,
            oauth_provider=provider,
            oauth_sub=user_info.sub,
            avatar_url=user_info.avatar_url,
            role=UserRole.GUEST,
        )
        db.add(user)
        await db.commit()
    else:
        # Update linked provider info and ensure the account is verified
        updated = False
        if user.oauth_provider is None:
            user.oauth_provider = provider
            user.oauth_sub = user_info.sub
            updated = True

        # Always update avatar and full_name from OAuth providers (Google/GitHub)
        if user_info.avatar_url and user.avatar_url != user_info.avatar_url:
            user.avatar_url = user_info.avatar_url
            updated = True
        if user_info.full_name and user.full_name != user_info.full_name:
            user.full_name = user_info.full_name
            updated = True

        # Mark email as verified (social providers guarantee verified email)
        if not user.is_verified:
            user.is_verified = True
            updated = True

        if updated:
            db.add(user)
            await db.commit()

    # Issue JWTs and session
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    # Ensure user.id is not None before passing to create_user_session
    if user.id is None:
        raise HTTPException(status_code=500, detail="User ID is required")
    tokens = await create_user_session(db, user, ip, ua)
    session_id = tokens["session_id"]

    additional_claims = {
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "oauth_provider": provider,
        "session_id": session_id,
    }

    access_token = create_access_token(subject=str(user.id), additional_claims=additional_claims)
    refresh_token = tokens["refresh_token"]

    # Store refresh token in session and as HttpOnly cookie
    # session_dict["refresh_token"] = refresh_token
    # await db.commit()

    response.set_cookie(
        "refresh_token",
        refresh_token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )

    # Redirect the browser to the frontend callback route with the tokens
    # Tokens are passed via query params so that the SPA (same origin as frontend)
    # can store them in localStorage. For production consider using a POST redirect
    # or other secure transfer.
    from urllib.parse import urlencode  # imported inline to avoid top-level import

    redirect_params = urlencode({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "success": "true",
    })

    frontend_callback = f"{settings.FRONTEND_BASE_URL}/oauth/{provider}/callback?{redirect_params}"
    return RedirectResponse(frontend_callback, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


# Removed /debug/{provider} endpoint used only for development
# @router.get("/debug/{provider}", summary="Debug OAuth callback URL")
# async def debug_oauth_callback(provider: str) -> Dict[str, str]:
#     """Debug endpoint to test OAuth callback URL generation."""
#     from urllib.parse import urlencode
#     
#     # Mock tokens for testing
#     access_token = "test_access_token"
#     refresh_token = "test_refresh_token"
#     
#     redirect_params = urlencode({
#         "access_token": access_token,
#         "refresh_token": refresh_token,
#         "success": "true",
#     })
#     
#     frontend_callback = f"{settings.FRONTEND_BASE_URL}/auth/oauth/{provider}/callback?{redirect_params}"
#     
#     return {
#         "frontend_base_url": settings.FRONTEND_BASE_URL,
#         "provider": provider,
#         "callback_url": frontend_callback,
#         "redirect_params": redirect_params
#     } 