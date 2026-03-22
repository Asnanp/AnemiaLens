from __future__ import annotations

import json
import logging
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr
from html import escape
from urllib import error as urllib_error
from urllib import request as urllib_request

from app.config import SCREENING_DISCLAIMER, settings

log = logging.getLogger("anemialens.email")


class EmailReportError(RuntimeError):
    """Base error for email report delivery problems."""


class EmailReportNotConfiguredError(EmailReportError):
    """Raised when the selected email provider is not configured."""


class EmailReportDeliveryError(EmailReportError):
    """Raised when the SMTP server rejects or fails a delivery."""


@dataclass(frozen=True)
class EmailReportContent:
    recipient: str
    share_text: str
    triage_label: str
    predicted_hemoglobin: float | None = None
    anemia_risk: float = 0.0


class EmailReportService:
    def is_configured(self) -> bool:
        if self._provider == "resend":
            return bool(settings.resend_api_key and self._from_email)
        return bool(
            settings.smtp_host
            and settings.smtp_username
            and settings.smtp_password
            and self._from_email
        )

    def masked_recipient(self, recipient: str) -> str:
        local, _, domain = recipient.partition("@")
        if not local or not domain:
            return "***"
        if len(local) <= 2:
            return f"{local[0]}*@{domain}"
        return f"{local[:2]}***@{domain}"

    def send_report(self, payload: EmailReportContent) -> None:
        if not self.is_configured():
            raise EmailReportNotConfiguredError(
                "Email delivery is not configured. Set the selected provider credentials in backend/.env or your deployment environment."
            )

        masked_recipient = self.masked_recipient(payload.recipient)
        log.info("[FIX] email report send started for %s", masked_recipient)

        try:
            if self._provider == "resend":
                self._send_via_resend(payload)
            else:
                self._send_via_smtp(payload)
        except smtplib.SMTPAuthenticationError as exc:
            log.error("[FIX] email report authentication failed for %s", masked_recipient)
            raise EmailReportDeliveryError(
                "SMTP authentication failed. Check the configured username, password, or app password."
            ) from exc
        except smtplib.SMTPRecipientsRefused as exc:
            log.warning("[FIX] email report recipient refused for %s", masked_recipient)
            raise EmailReportDeliveryError(
                "The SMTP server rejected the recipient address."
            ) from exc
        except (smtplib.SMTPException, OSError) as exc:
            log.exception("[FIX] email report transport failed for %s", masked_recipient)
            raise EmailReportDeliveryError(
                "Could not deliver the email through the configured SMTP server."
            ) from exc

        log.info("[FIX] email report sent successfully to %s", masked_recipient)

    @property
    def _provider(self) -> str:
        return settings.email_provider.strip().lower()

    @property
    def _from_email(self) -> str:
        return settings.email_from_email or settings.smtp_username

    def _send_via_smtp(self, payload: EmailReportContent) -> None:
        message = self._build_message(payload)
        if settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(
                settings.smtp_host,
                settings.smtp_port,
                timeout=settings.smtp_timeout,
                context=ssl.create_default_context(),
            ) as server:
                self._deliver(server, message)
        else:
            with smtplib.SMTP(
                settings.smtp_host,
                settings.smtp_port,
                timeout=settings.smtp_timeout,
            ) as server:
                server.ehlo()
                if settings.smtp_use_starttls:
                    server.starttls(context=ssl.create_default_context())
                    server.ehlo()
                self._deliver(server, message)

    def _send_via_resend(self, payload: EmailReportContent) -> None:
        request = urllib_request.Request(
            url=f"{settings.resend_api_base.rstrip('/')}/emails",
            data=json.dumps(self._build_resend_payload(payload)).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
                "Idempotency-Key": self._idempotency_key(payload),
            },
            method="POST",
        )
        try:
            with urllib_request.urlopen(request, timeout=settings.smtp_timeout) as response:
                response.read()
        except urllib_error.HTTPError as exc:
            detail = self._extract_provider_error(exc.read().decode("utf-8", errors="replace"))
            raise EmailReportDeliveryError(
                f"Email provider rejected the request: {detail or f'HTTP {exc.code}'}"
            ) from exc
        except urllib_error.URLError as exc:
            raise EmailReportDeliveryError(
                "Could not reach the configured email provider."
            ) from exc

    def _build_resend_payload(self, payload: EmailReportContent) -> dict[str, object]:
        body: dict[str, object] = {
            "from": formataddr((settings.email_from_name, self._from_email)),
            "to": [payload.recipient],
            "subject": self._subject(payload),
            "html": self._build_html(payload),
            "text": self._build_plain_text(payload),
        }
        if settings.email_reply_to:
            body["reply_to"] = settings.email_reply_to
        return body

    def _idempotency_key(self, payload: EmailReportContent) -> str:
        safe_label = payload.triage_label.lower().replace(" ", "-")
        return f"email-report/{payload.recipient.lower()}/{safe_label}"[:256]

    def _build_message(self, payload: EmailReportContent) -> EmailMessage:
        message = EmailMessage()
        message["Subject"] = self._subject(payload)
        message["From"] = formataddr((settings.email_from_name, self._from_email))
        message["To"] = payload.recipient
        if settings.email_reply_to:
            message["Reply-To"] = settings.email_reply_to

        plain_body = self._build_plain_text(payload)
        html_body = self._build_html(payload)

        message.set_content(plain_body)
        message.add_alternative(html_body, subtype="html")
        return message

    def _subject(self, payload: EmailReportContent) -> str:
        return f"AnemiaLens Screening Report - {payload.triage_label}"

    def _build_plain_text(self, payload: EmailReportContent) -> str:
        hb_line = self._hemoglobin_line(payload.predicted_hemoglobin)
        risk_pct = round(payload.anemia_risk * 100)
        return (
            "AnemiaLens Screening Result Report\n"
            "================================\n\n"
            f"Triage Label: {payload.triage_label}\n"
            f"Anemia Risk Score: {risk_pct}%\n"
            f"{hb_line}\n\n"
            "Summary\n"
            "-------\n"
            f"{payload.share_text.strip()}\n\n"
            "Important\n"
            "---------\n"
            f"{SCREENING_DISCLAIMER} Please confirm results with a clinical blood test (CBC).\n\n"
            "AnemiaLens\n"
            "https://anemia-lens.vercel.app\n"
        )

    def _build_html(self, payload: EmailReportContent) -> str:
        hb_label, hb_value = self._hemoglobin_parts(payload.predicted_hemoglobin)
        risk_pct = round(payload.anemia_risk * 100)
        share_html = "<br />".join(
            escape(line) for line in payload.share_text.strip().splitlines() if line.strip()
        )
        return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>AnemiaLens Screening Report</title>
  </head>
  <body style="margin:0;padding:0;background:#0d0d0d;color:#edede8;font-family:Arial,sans-serif;">
    <div style="max-width:600px;margin:0 auto;padding:32px 24px;">
      <div style="border-bottom:2px solid #c8001e;padding-bottom:16px;margin-bottom:24px;">
        <div style="font-size:22px;font-weight:700;color:#c8001e;letter-spacing:-0.03em;">AnemiaLens</div>
        <div style="font-size:12px;color:#888;margin-top:4px;">Screening Result Report</div>
      </div>
      <div style="display:inline-block;padding:6px 16px;border-radius:999px;font-size:12px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;background:rgba(200,0,30,0.15);border:1px solid rgba(200,0,30,0.4);color:#ff6b7b;">
        {escape(payload.triage_label)}
      </div>
      <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:16px 20px;margin:12px 0;">
        <div style="font-size:11px;color:#888;text-transform:uppercase;letter-spacing:0.12em;margin-bottom:4px;">Anemia Risk Score</div>
        <div style="font-size:20px;font-weight:700;color:#edede8;">{risk_pct}%</div>
      </div>
      <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:16px 20px;margin:12px 0;">
        <div style="font-size:11px;color:#888;text-transform:uppercase;letter-spacing:0.12em;margin-bottom:4px;">{escape(hb_label)}</div>
        <div style="font-size:20px;font-weight:700;color:#edede8;">{escape(hb_value)}</div>
      </div>
      <div style="background:rgba(255,255,255,0.02);border-left:3px solid #c8001e;border-radius:8px;padding:16px 20px;margin:20px 0;font-size:13px;line-height:1.7;color:#d6d6cf;">
        {share_html}
      </div>
      <div style="font-size:11px;color:#9b9b93;line-height:1.6;margin-top:24px;padding:12px 16px;border:1px solid rgba(255,255,255,0.06);border-radius:8px;">
        <strong>Important:</strong> {escape(SCREENING_DISCLAIMER)} Please confirm results with a clinical blood test (CBC).
      </div>
      <div style="margin-top:32px;padding-top:16px;border-top:1px solid rgba(255,255,255,0.06);font-size:11px;color:#777;text-align:center;">
        AnemiaLens · https://anemia-lens.vercel.app · No lab. No needle. Just a smartphone.
      </div>
    </div>
  </body>
</html>"""

    def _hemoglobin_parts(self, predicted_hemoglobin: float | None) -> tuple[str, str]:
        if predicted_hemoglobin is None:
            return ("Estimated Hemoglobin", "Not available (high uncertainty)")
        return ("Estimated Hemoglobin", f"{predicted_hemoglobin:.1f} g/dL")

    def _hemoglobin_line(self, predicted_hemoglobin: float | None) -> str:
        label, value = self._hemoglobin_parts(predicted_hemoglobin)
        return f"{label}: {value}"

    def _deliver(self, server: smtplib.SMTP, message: EmailMessage) -> None:
        server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)

    def _extract_provider_error(self, raw_body: str) -> str | None:
        try:
            body = json.loads(raw_body)
        except json.JSONDecodeError:
            body = None
        if isinstance(body, dict):
            for key in ("message", "error", "name"):
                value = body.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        stripped = raw_body.strip()
        return stripped or None
