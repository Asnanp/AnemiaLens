"""
Email report API route.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from app.services.email_report import (
    EmailReportContent,
    EmailReportDeliveryError,
    EmailReportNotConfiguredError,
    EmailReportService,
)

log = logging.getLogger("anemialens.email")

router = APIRouter(prefix="/api", tags=["email"])

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class EmailReportRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    share_text: str = Field(min_length=20, max_length=6000)
    triage_label: str = Field(min_length=2, max_length=80)
    predicted_hemoglobin: float | None = Field(default=None, ge=0.0, le=30.0)
    anemia_risk: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not _EMAIL_RE.fullmatch(normalized):
            raise ValueError("Enter a valid email address.")
        return normalized

    @field_validator("share_text", "triage_label")
    @classmethod
    def _strip_non_empty(cls, value: str) -> str:
        normalized = value.replace("\r\n", "\n").strip()
        if not normalized:
            raise ValueError("This field cannot be blank.")
        return normalized


class EmailReportResponse(BaseModel):
    status: Literal["sent"]
    message: str


def get_email_report_service() -> EmailReportService:
    return EmailReportService()


@router.post(
    "/email-report",
    response_model=EmailReportResponse,
    summary="Send a screening result summary by email",
    status_code=status.HTTP_200_OK,
)
async def send_email_report(
    payload: EmailReportRequest,
    service: Annotated[EmailReportService, Depends(get_email_report_service)],
) -> EmailReportResponse:
    masked_recipient = service.masked_recipient(payload.email)
    log.info("[FIX] email report request received for %s", masked_recipient)

    try:
        await asyncio.to_thread(
            service.send_report,
            EmailReportContent(
                recipient=payload.email,
                share_text=payload.share_text,
                triage_label=payload.triage_label,
                predicted_hemoglobin=payload.predicted_hemoglobin,
                anemia_risk=payload.anemia_risk,
            ),
        )
    except EmailReportNotConfiguredError as exc:
        log.warning("[FIX] email report unavailable for %s: %s", masked_recipient, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except EmailReportDeliveryError as exc:
        log.error("[FIX] email report delivery failed for %s: %s", masked_recipient, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return EmailReportResponse(
        status="sent",
        message=f"Report sent to {payload.email}.",
    )
