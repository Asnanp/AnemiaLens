"""
Tests for the email report API and SMTP delivery service.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.api.email_report import get_email_report_service, router
from app.config import settings
from app.services import email_report as email_report_module
from app.services.email_report import (
    EmailReportContent,
    EmailReportDeliveryError,
    EmailReportNotConfiguredError,
    EmailReportService,
)


class _StubRouterService:
    def __init__(self, exc: Exception | None = None) -> None:
        self.exc = exc
        self.payload: EmailReportContent | None = None

    def masked_recipient(self, recipient: str) -> str:
        return f"masked:{recipient}"

    def send_report(self, payload: EmailReportContent) -> None:
        self.payload = payload
        if self.exc is not None:
            raise self.exc


class _SMTPStub:
    last_instance: "_SMTPStub | None" = None

    def __init__(self, host: str, port: int, timeout: float | None = None, context=None) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.context = context
        self.logged_in: tuple[str, str] | None = None
        self.sent_message = None
        _SMTPStub.last_instance = self

    def __enter__(self) -> "_SMTPStub":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def login(self, username: str, password: str) -> None:
        self.logged_in = (username, password)

    def send_message(self, message) -> None:
        self.sent_message = message


def _client_with_service(service: _StubRouterService) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_email_report_service] = lambda: service
    return TestClient(app)


def test_email_report_endpoint_sends_valid_payload() -> None:
    service = _StubRouterService()
    client = _client_with_service(service)

    response = client.post(
        "/api/email-report",
        json={
            "email": "person@example.com",
            "share_text": "Moderate risk summary.\nPlease follow up with a CBC test.",
            "triage_label": "Moderate Risk",
            "predicted_hemoglobin": 10.6,
            "anemia_risk": 0.54,
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "sent"
    assert service.payload is not None
    assert service.payload.recipient == "person@example.com"
    assert service.payload.predicted_hemoglobin == 10.6


def test_email_report_endpoint_rejects_invalid_email() -> None:
    client = _client_with_service(_StubRouterService())

    response = client.post(
        "/api/email-report",
        json={
            "email": "not-an-email",
            "share_text": "Moderate risk summary.\nPlease follow up with a CBC test.",
            "triage_label": "Moderate Risk",
            "predicted_hemoglobin": 10.6,
            "anemia_risk": 0.54,
        },
    )

    assert response.status_code == 422


def test_email_report_endpoint_returns_503_when_not_configured() -> None:
    client = _client_with_service(
        _StubRouterService(
            EmailReportNotConfiguredError("Email delivery is not configured."),
        )
    )

    response = client.post(
        "/api/email-report",
        json={
            "email": "person@example.com",
            "share_text": "Moderate risk summary.\nPlease follow up with a CBC test.",
            "triage_label": "Moderate Risk",
            "predicted_hemoglobin": 10.6,
            "anemia_risk": 0.54,
        },
    )

    assert response.status_code == 503
    assert "not configured" in response.json()["detail"].lower()


def test_email_report_endpoint_returns_502_when_delivery_fails() -> None:
    client = _client_with_service(
        _StubRouterService(
            EmailReportDeliveryError("SMTP authentication failed."),
        )
    )

    response = client.post(
        "/api/email-report",
        json={
            "email": "person@example.com",
            "share_text": "Moderate risk summary.\nPlease follow up with a CBC test.",
            "triage_label": "Moderate Risk",
            "predicted_hemoglobin": 10.6,
            "anemia_risk": 0.54,
        },
    )

    assert response.status_code == 502
    assert "smtp" in response.json()["detail"].lower()


def test_email_report_service_requires_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "smtp_username", "")
    monkeypatch.setattr(settings, "smtp_password", "")
    monkeypatch.setattr(settings, "email_from_email", "")

    service = EmailReportService()

    with pytest.raises(EmailReportNotConfiguredError, match="configured"):
        service.send_report(
            EmailReportContent(
                recipient="person@example.com",
                share_text="Moderate risk summary.\nPlease follow up with a CBC test.",
                triage_label="Moderate Risk",
                predicted_hemoglobin=10.6,
                anemia_risk=0.54,
            )
        )


def test_email_report_service_sends_email_via_ssl(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_port", 465)
    monkeypatch.setattr(settings, "smtp_username", "mailer@example.com")
    monkeypatch.setattr(settings, "smtp_password", "app-password")
    monkeypatch.setattr(settings, "smtp_use_ssl", True)
    monkeypatch.setattr(settings, "smtp_use_starttls", False)
    monkeypatch.setattr(settings, "smtp_timeout", 20.0)
    monkeypatch.setattr(settings, "email_from_name", "AnemiaLens")
    monkeypatch.setattr(settings, "email_from_email", "reports@example.com")
    monkeypatch.setattr(settings, "email_reply_to", "support@example.com")
    monkeypatch.setattr(email_report_module.smtplib, "SMTP_SSL", _SMTPStub)

    service = EmailReportService()
    service.send_report(
        EmailReportContent(
            recipient="patient@example.com",
            share_text="Moderate risk summary.\nPlease follow up with a CBC test.",
            triage_label="Moderate Risk",
            predicted_hemoglobin=10.6,
            anemia_risk=0.54,
        )
    )

    smtp = _SMTPStub.last_instance
    assert smtp is not None
    assert smtp.host == "smtp.example.com"
    assert smtp.port == 465
    assert smtp.logged_in == ("mailer@example.com", "app-password")
    assert smtp.sent_message["To"] == "patient@example.com"
    assert smtp.sent_message["Reply-To"] == "support@example.com"
    assert "Moderate Risk" in smtp.sent_message["Subject"]
    plain_part = smtp.sent_message.get_body(preferencelist=("plain",))
    html_part = smtp.sent_message.get_body(preferencelist=("html",))
    assert plain_part is not None
    assert html_part is not None
    assert "CBC test" in plain_part.get_content()
    assert "<br />" in html_part.get_content()
