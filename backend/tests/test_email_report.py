"""
Tests for the email report API and delivery service.
"""

from __future__ import annotations

import json
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


class _HTTPResponseStub:
    def __init__(self, body: str = '{"id":"email_123"}', status: int = 200) -> None:
        self._body = body.encode("utf-8")
        self.status = status

    def read(self) -> bytes:
        return self._body


class _HTTPSConnectionStub:
    last_instance: "_HTTPSConnectionStub | None" = None
    response_status: int = 200
    response_body: str = '{"id":"email_123"}'

    def __init__(self, host: str, timeout: float | None = None) -> None:
        self.host = host
        self.timeout = timeout
        self.request_args: tuple[str, str, bytes, dict[str, str]] | None = None
        self.closed = False
        _HTTPSConnectionStub.last_instance = self

    def request(self, method: str, path: str, body=None, headers=None) -> None:
        self.request_args = (method, path, body, headers or {})

    def getresponse(self) -> _HTTPResponseStub:
        return _HTTPResponseStub(body=self.response_body, status=self.response_status)

    def close(self) -> None:
        self.closed = True


class _GmailHTTPSConnectionStub:
    requests: list[tuple[str, str, bytes, dict[str, str], str, float | None]] = []
    response_queue: list[_HTTPResponseStub] = []

    def __init__(self, host: str, timeout: float | None = None) -> None:
        self.host = host
        self.timeout = timeout
        self.closed = False

    def request(self, method: str, path: str, body=None, headers=None) -> None:
        _GmailHTTPSConnectionStub.requests.append((method, path, body, headers or {}, self.host, self.timeout))

    def getresponse(self) -> _HTTPResponseStub:
        return _GmailHTTPSConnectionStub.response_queue.pop(0)

    def close(self) -> None:
        self.closed = True


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
    monkeypatch.setattr(settings, "email_provider", "smtp")
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
    monkeypatch.setattr(settings, "email_provider", "smtp")
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
    assert "clinical blood test (CBC)" in plain_part.get_content()
    assert "Recommended Next Steps" in plain_part.get_content()
    assert "Why this result" in html_part.get_content()
    assert "Open AnemiaLens" in html_part.get_content()


def test_email_report_service_sends_email_via_resend(monkeypatch: pytest.MonkeyPatch) -> None:
    _HTTPSConnectionStub.response_status = 200
    _HTTPSConnectionStub.response_body = '{"id":"email_123"}'
    monkeypatch.setattr(settings, "email_provider", "resend")
    monkeypatch.setattr(settings, "resend_api_key", "re_test_123")
    monkeypatch.setattr(settings, "resend_api_base", "https://api.resend.test")
    monkeypatch.setattr(settings, "email_from_name", "AnemiaLens")
    monkeypatch.setattr(settings, "email_from_email", "onboarding@resend.dev")
    monkeypatch.setattr(settings, "email_reply_to", "support@example.com")
    monkeypatch.setattr(settings, "smtp_username", "")
    monkeypatch.setattr(settings, "smtp_password", "")
    monkeypatch.setattr(settings, "smtp_timeout", 12.0)
    monkeypatch.setattr(email_report_module.http.client, "HTTPSConnection", _HTTPSConnectionStub)

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

    connection = _HTTPSConnectionStub.last_instance
    assert connection is not None
    assert connection.host == "api.resend.test"
    assert connection.timeout == 12.0
    assert connection.closed is True
    assert connection.request_args is not None
    method, path, raw_body, headers = connection.request_args
    body = json.loads(raw_body.decode("utf-8"))
    assert method == "POST"
    assert path == "/emails"
    assert headers["Authorization"] == "Bearer re_test_123"
    assert headers["Content-Type"] == "application/json"
    assert headers["Idempotency-Key"].startswith("email-report/patient@example.com/moderate-risk/")
    assert headers["User-Agent"] == "AnemiaLens/1.0 (+https://anemia-lens.vercel.app)"
    assert body["from"] == "AnemiaLens <onboarding@resend.dev>"
    assert body["to"] == ["patient@example.com"]
    assert body["reply_to"] == "support@example.com"
    assert body["subject"] == "AnemiaLens Screening Report - Moderate Risk"
    assert "clinical blood test (CBC)" in body["text"]


def test_email_report_service_sends_email_via_sendgrid(monkeypatch: pytest.MonkeyPatch) -> None:
    _HTTPSConnectionStub.response_status = 202
    _HTTPSConnectionStub.response_body = ""
    monkeypatch.setattr(settings, "email_provider", "sendgrid")
    monkeypatch.setattr(settings, "sendgrid_api_key", "SG.test-key")
    monkeypatch.setattr(settings, "sendgrid_api_base", "https://api.sendgrid.test/v3")
    monkeypatch.setattr(settings, "email_from_name", "AnemiaLens")
    monkeypatch.setattr(settings, "email_from_email", "asnanp875@gmail.com")
    monkeypatch.setattr(settings, "email_reply_to", "asnanp875@gmail.com")
    monkeypatch.setattr(settings, "smtp_username", "")
    monkeypatch.setattr(settings, "smtp_password", "")
    monkeypatch.setattr(settings, "smtp_timeout", 12.0)
    monkeypatch.setattr(email_report_module.http.client, "HTTPSConnection", _HTTPSConnectionStub)

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

    connection = _HTTPSConnectionStub.last_instance
    assert connection is not None
    assert connection.host == "api.sendgrid.test"
    assert connection.timeout == 12.0
    assert connection.closed is True
    assert connection.request_args is not None
    method, path, raw_body, headers = connection.request_args
    body = json.loads(raw_body.decode("utf-8"))
    assert method == "POST"
    assert path == "/v3/mail/send"
    assert headers["Authorization"] == "Bearer SG.test-key"
    assert headers["Content-Type"] == "application/json"
    assert headers["User-Agent"] == "AnemiaLens/1.0 (+https://anemia-lens.vercel.app)"
    assert body["from"] == {"email": "asnanp875@gmail.com", "name": "AnemiaLens"}
    assert body["reply_to"] == {"email": "asnanp875@gmail.com"}
    assert body["personalizations"][0]["to"] == [{"email": "patient@example.com"}]
    assert body["personalizations"][0]["subject"] == "AnemiaLens Screening Report - Moderate Risk"
    assert body["content"][0]["type"] == "text/plain"
    assert body["content"][1]["type"] == "text/html"
    assert "clinical blood test (CBC)" in body["content"][0]["value"]


def test_email_report_service_sends_email_via_gmail_api(monkeypatch: pytest.MonkeyPatch) -> None:
    _GmailHTTPSConnectionStub.requests = []
    _GmailHTTPSConnectionStub.response_queue = [
        _HTTPResponseStub(body='{"access_token":"ya29.test-token"}', status=200),
        _HTTPResponseStub(body='{"id":"gmail_message_123"}', status=200),
    ]
    monkeypatch.setattr(settings, "email_provider", "gmail_api")
    monkeypatch.setattr(settings, "gmail_client_id", "client-id")
    monkeypatch.setattr(settings, "gmail_client_secret", "client-secret")
    monkeypatch.setattr(settings, "gmail_refresh_token", "refresh-token")
    monkeypatch.setattr(settings, "gmail_token_url", "https://oauth2.googleapis.com/token")
    monkeypatch.setattr(settings, "gmail_api_base", "https://gmail.googleapis.com/gmail/v1")
    monkeypatch.setattr(settings, "email_from_name", "AnemiaLens")
    monkeypatch.setattr(settings, "email_from_email", "asnanp875@gmail.com")
    monkeypatch.setattr(settings, "email_reply_to", "asnanp875@gmail.com")
    monkeypatch.setattr(settings, "smtp_timeout", 12.0)
    monkeypatch.setattr(email_report_module.http.client, "HTTPSConnection", _GmailHTTPSConnectionStub)

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

    assert len(_GmailHTTPSConnectionStub.requests) == 2

    token_method, token_path, token_body, token_headers, token_host, token_timeout = _GmailHTTPSConnectionStub.requests[0]
    assert token_method == "POST"
    assert token_host == "oauth2.googleapis.com"
    assert token_timeout == 12.0
    assert token_path == "/token"
    assert token_headers["Content-Type"] == "application/x-www-form-urlencoded"
    assert b"grant_type=refresh_token" in token_body
    assert b"client_id=client-id" in token_body
    assert b"client_secret=client-secret" in token_body
    assert b"refresh_token=refresh-token" in token_body

    send_method, send_path, send_body_raw, send_headers, send_host, send_timeout = _GmailHTTPSConnectionStub.requests[1]
    send_body = json.loads(send_body_raw.decode("utf-8"))
    assert send_method == "POST"
    assert send_host == "gmail.googleapis.com"
    assert send_timeout == 12.0
    assert send_path == "/gmail/v1/users/me/messages/send"
    assert send_headers["Authorization"] == "Bearer ya29.test-token"
    assert send_headers["Content-Type"] == "application/json"
    assert "raw" in send_body
