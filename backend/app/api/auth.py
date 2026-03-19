"""
Authentication API routes — register, login, refresh, me.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
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

        access_token = create_access_token({"sub": user.uid, "role": user.role})
        refresh_token = create_refresh_token({"sub": user.uid})
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=3600,
        )
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("Registration failed for %s", body.email)
        # Avoid misleading "Database connection error" if it's a code/logic error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during account creation. Please try again later.",
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

    access_token = create_access_token({"sub": user.uid, "role": user.role})
    refresh_token = create_refresh_token({"sub": user.uid})
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=3600,
    )


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

    access_token = create_access_token({"sub": user.uid, "role": user.role})
    refresh_token = create_refresh_token({"sub": user.uid})
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=3600,
    )


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

from sqlalchemy import func as sa_func
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
