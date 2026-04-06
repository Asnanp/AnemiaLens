"""
FastAPI dependencies — authentication, database session, current user,
and service-layer dependency injection.

This module provides:
- Auth dependencies (get_current_user, get_optional_user, require_admin)
- Service container access for ML pipeline services
- Typed FastAPI Depends() helpers for clean route signatures.

Usage in routes:
    from app.dependencies import get_predictor, get_triage_service

    @router.post("/analyze")
    async def analyze(
        predictor: ScreeningPredictor = Depends(get_predictor),
        triage: TriageService = Depends(get_triage_service),
    ):
        ...
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, TYPE_CHECKING

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.utils.security import decode_token

if TYPE_CHECKING:
    from app.services.case_insight import CaseInsightService
    from app.services.clinical_brief import ClinicalBriefService
    from app.services.guidance import GuidanceService
    from app.services.handoff import HandoffSummaryService
    from app.services.image_quality import ImageQualityService
    from app.services.patient_case import PatientCaseService
    from app.services.prediction import ScreeningPredictor
    from app.services.triage import TriageService

# ---------------------------------------------------------------------------
# Security scheme (Bearer token)
# ---------------------------------------------------------------------------

_bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Get current user from JWT
# ---------------------------------------------------------------------------

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Validates the Bearer token and returns the authenticated User.
    Raises 401 if token is missing, expired, or user not found.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_uid = payload.get("sub")
    if not user_uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
        )

    result = await db.execute(select(User).where(User.uid == user_uid))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated.",
        )
    return user


# ---------------------------------------------------------------------------
# Optional user (for endpoints that work with or without auth)
# ---------------------------------------------------------------------------

async def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User | None:
    """
    Returns the authenticated user if a valid token is present, None otherwise.
    Does NOT raise — use this for endpoints that serve both authenticated and anonymous users.
    """
    if credentials is None:
        return None

    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        return None

    user_uid = payload.get("sub")
    if not user_uid:
        return None

    result = await db.execute(select(User).where(User.uid == user_uid))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        return None
    return user


# ---------------------------------------------------------------------------
# Admin-only guard
# ---------------------------------------------------------------------------

async def require_admin(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Raises 403 if the authenticated user is not an admin."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return user


# ---------------------------------------------------------------------------
# Service container — typed access to ML pipeline services
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScreeningServices:
    """
    Read-only container for all ML pipeline services attached to the FastAPI app.

    Obtained via ``get_services(request)`` in route handlers.
    Individual services are accessible as properties:

        services = get_services(request)
        predictor = services.predictor
        triage = services.triage_service
    """

    _request: Request = field(repr=False)

    @property
    def predictor(self) -> "ScreeningPredictor":
        return self._request.app.state.predictor

    @property
    def quality_service(self) -> "ImageQualityService":
        return self._request.app.state.quality_service

    @property
    def triage_service(self) -> "TriageService":
        return self._request.app.state.triage_service

    @property
    def guidance_service(self) -> "GuidanceService":
        return self._request.app.state.guidance_service

    @property
    def case_insight_service(self) -> "CaseInsightService":
        return self._request.app.state.case_insight_service

    @property
    def clinical_brief_service(self) -> "ClinicalBriefService":
        return self._request.app.state.clinical_brief_service

    @property
    def handoff_service(self) -> "HandoffSummaryService":
        return self._request.app.state.handoff_service

    @property
    def patient_case_service(self) -> "PatientCaseService":
        return self._request.app.state.patient_case_service


def get_services(request: Request) -> ScreeningServices:
    """
    FastAPI dependency that returns a typed service container.

    Usage:
        services: ScreeningServices = Depends(get_services)
    """
    return ScreeningServices(_request=request)


# ---------------------------------------------------------------------------
# Individual service dependencies (for routes that need only one service)
# ---------------------------------------------------------------------------


async def get_predictor(request: Request) -> "ScreeningPredictor":
    """Returns the ML screening predictor from app state."""
    return request.app.state.predictor


async def get_quality_service(request: Request) -> "ImageQualityService":
    """Returns the image quality service from app state."""
    return request.app.state.quality_service


async def get_triage_service(request: Request) -> "TriageService":
    """Returns the triage service from app state."""
    return request.app.state.triage_service


async def get_guidance_service(request: Request) -> "GuidanceService":
    """Returns the guidance service from app state."""
    return request.app.state.guidance_service


async def get_case_insight_service(request: Request) -> "CaseInsightService":
    """Returns the case insight service from app state."""
    return request.app.state.case_insight_service


async def get_clinical_brief_service(request: Request) -> "ClinicalBriefService":
    """Returns the clinical brief service from app state."""
    return request.app.state.clinical_brief_service


async def get_handoff_service(request: Request) -> "HandoffSummaryService":
    """Returns the handoff summary service from app state."""
    return request.app.state.handoff_service


async def get_patient_case_service(request: Request) -> "PatientCaseService":
    """Returns the patient case service from app state."""
    return request.app.state.patient_case_service
