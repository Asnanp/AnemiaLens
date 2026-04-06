"""
Authentication API routes — register, login, refresh, me.
"""

from __future__ import annotations

import asyncio
import logging
import os
import secrets
from datetime import datetime, timezone
from typing import Annotated, Any

import requests
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.utils.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

log = logging.getLogger("anemialens.auth")

router = APIRouter(prefix="/api/auth", tags=["auth"])

# SECURITY: Google OAuth config must be set via environment variables
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_TOKENINFO_URL = os.getenv("GOOGLE_TOKENINFO_URL", "https://oauth2.googleapis.com/tokeninfo")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class GoogleLoginRequest(BaseModel):
    credential: str = Field(min_length=20, max_length=4096)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class UserProfile(BaseModel):
    uid: str
    email: str
    full_name: str | None
    role: str
    subscription_tier: str
    scan_count: int
    created_at: str
    last_login_at: str | None


class GoogleIdentity(BaseModel):
    email: str
    email_verified: bool
    full_name: str | None = None


def _parse_google_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() == "true"
    if isinstance(value, (int, float)):
        return bool(value)
    return False


def _token_response_for_user(user: User) -> TokenResponse:
    access_token = create_access_token({"sub": user.uid, "role": user.role})
    refresh_token = create_refresh_token({"sub": user.uid})
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=3600,
    )


def _google_http_error(
    detail: str,
    status_code: int = status.HTTP_401_UNAUTHORIZED,
) -> HTTPException:
    return HTTPException(status_code=status_code, detail=detail)


def _verify_google_id_token(credential: str) -> GoogleIdentity:
    google_client_id = (
        os.getenv("ANEMIALENS_GOOGLE_CLIENT_ID")
        or os.getenv("GOOGLE_CLIENT_ID")
        or os.getenv("VITE_GOOGLE_CLIENT_ID")
        or GOOGLE_CLIENT_ID
    )
    google_tokeninfo_url = (
        os.getenv("ANEMIALENS_GOOGLE_TOKENINFO_URL")
        or os.getenv("GOOGLE_TOKENINFO_URL")
        or GOOGLE_TOKENINFO_URL
    )

    if not google_client_id:
        raise _google_http_error(
            "Google sign-in is not configured for this deployment.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    try:
        response = requests.get(
            google_tokeninfo_url,
            params={"id_token": credential},
            timeout=10,
        )
    except requests.RequestException as exc:
        log.exception("Google token verification request failed")
        raise _google_http_error(
            "Google sign-in is temporarily unavailable. Please try again.",
            status.HTTP_502_BAD_GATEWAY,
        ) from exc

    try:
        raw_payload: dict[str, Any] = response.json()
    except ValueError as exc:
        raise _google_http_error(
            "Google sign-in returned an invalid response.",
            status.HTTP_502_BAD_GATEWAY,
        ) from exc

    if response.status_code >= 400:
        provider_message = raw_payload.get("error_description") or raw_payload.get("error")
        message = (
            str(provider_message).strip()
            if isinstance(provider_message, str) and provider_message.strip()
            else "Google sign-in failed. Please try again."
        )
        raise _google_http_error(message)

    audience = raw_payload.get("aud")
    if audience != google_client_id:
        raise _google_http_error("Google credential is not valid for this app.")

    email = raw_payload.get("email")
    if not isinstance(email, str) or not email.strip():
        raise _google_http_error("Google sign-in did not return an email address.")

    if not _parse_google_bool(raw_payload.get("email_verified")):
        raise _google_http_error("Google account email is not verified.")

    full_name = raw_payload.get("name")
    if not isinstance(full_name, str):
        full_name = None

    return GoogleIdentity(
        email=email.strip().lower(),
        email_verified=True,
        full_name=full_name.strip() if full_name else None,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user account",
)
async def register(
    body: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    log.info("Received registration request for email: %s", body.email)
    try:
        # Check if email already exists
        result = await db.execute(select(User).where(User.email == body.email.lower().strip()))
        if result.scalar_one_or_none() is not None:
            log.warning("Registration failed: Email already exists - %s", body.email)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            )

        user = User(
            email=body.email.lower().strip(),
            hashed_password=hash_password(body.password),
            full_name=body.full_name,
            role="user",
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)

        log.info("User registered successfully: %s (uid=%s)", user.email, user.uid)

        return _token_response_for_user(user)
    except HTTPException:
        raise
    except Exception:
        log.exception("Registration failed for %s", body.email)
        # SECURITY: Don't leak internal error details to clients
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again or contact support if the problem persists.",
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and get tokens",
)
async def login(
    body: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    result = await db.execute(
        select(User).where(User.email == body.email.lower().strip())
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated.",
        )

    user.last_login_at = datetime.now(timezone.utc)
    await db.flush()

    log.info("User login: %s (uid=%s)", user.email, user.uid)

    return _token_response_for_user(user)


@router.post(
    "/google",
    response_model=TokenResponse,
    summary="Authenticate with Google Sign-In",
)
async def login_with_google(
    body: GoogleLoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    identity = await asyncio.to_thread(_verify_google_id_token, body.credential)
    normalized_email = str(identity.email).lower().strip()

    result = await db.execute(select(User).where(User.email == normalized_email))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            email=normalized_email,
            hashed_password=hash_password(secrets.token_urlsafe(32)),
            full_name=identity.full_name,
            role="user",
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        log.info("Created account from Google sign-in: %s (uid=%s)", user.email, user.uid)
    elif identity.full_name and not user.full_name:
        user.full_name = identity.full_name

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated.",
        )

    user.last_login_at = datetime.now(timezone.utc)
    await db.flush()

    log.info("Google login: %s (uid=%s)", user.email, user.uid)
    return _token_response_for_user(user)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh an expired access token",
)
async def refresh(
    body: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    payload = decode_token(body.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )

    user_uid = payload.get("sub")
    result = await db.execute(select(User).where(User.uid == user_uid))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )

    return _token_response_for_user(user)


@router.get(
    "/me",
    response_model=UserProfile,
    summary="Get current user profile",
)
async def me(
    user: Annotated[User, Depends(get_current_user)],
) -> UserProfile:
    return UserProfile(
        uid=user.uid,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        subscription_tier=user.subscription_tier or "free",
        scan_count=user.scan_count,
        created_at=user.created_at.isoformat(),
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
    )


# ---------------------------------------------------------------------------
# Personal stats
# ---------------------------------------------------------------------------

from app.models.screening import Screening


class UserStatsResponse(BaseModel):
    total_scans: int
    scans_this_month: int
    avg_risk: float | None
    avg_hemoglobin: float | None
    high_concern_count: int
    low_risk_count: int
    last_scan_at: str | None


@router.get(
    "/me/stats",
    response_model=UserStatsResponse,
    summary="Get personal screening statistics",
)
async def me_stats(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserStatsResponse:
    from datetime import datetime, timezone
    from sqlalchemy import select, func, and_

    # Total scans
    total = await db.scalar(
        select(func.count()).where(Screening.user_id == user.id)
    ) or 0

    # This month
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    this_month = await db.scalar(
        select(func.count()).where(
            and_(Screening.user_id == user.id, Screening.created_at >= month_start)
        )
    ) or 0

    # Averages
    avg_risk = await db.scalar(
        select(func.avg(Screening.anemia_risk)).where(
            and_(Screening.user_id == user.id, Screening.anemia_risk.isnot(None))
        )
    )
    avg_hb = await db.scalar(
        select(func.avg(Screening.predicted_hemoglobin)).where(
            and_(Screening.user_id == user.id, Screening.predicted_hemoglobin.isnot(None))
        )
    )

    # Band counts
    high = await db.scalar(
        select(func.count()).where(
            and_(Screening.user_id == user.id, Screening.triage_band == "high_concern")
        )
    ) or 0
    low = await db.scalar(
        select(func.count()).where(
            and_(Screening.user_id == user.id, Screening.triage_band == "low_risk")
        )
    ) or 0

    # Last scan
    last = await db.scalar(
        select(Screening.created_at).where(Screening.user_id == user.id)
        .order_by(Screening.created_at.desc()).limit(1)
    )

    return UserStatsResponse(
        total_scans=total,
        scans_this_month=this_month,
        avg_risk=round(float(avg_risk), 4) if avg_risk is not None else None,
        avg_hemoglobin=round(float(avg_hb), 2) if avg_hb is not None else None,
        high_concern_count=high,
        low_risk_count=low,
        last_scan_at=last.isoformat() if last else None,
    )
