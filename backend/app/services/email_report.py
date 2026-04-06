from __future__ import annotations

import base64
import json
import http.client
import hashlib
import logging
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr
from html import escape
from urllib.parse import urlencode, urlsplit

from app.config import SCREENING_DISCLAIMER, settings

log = logging.getLogger("anemialens.email")


class EmailReportError(RuntimeError):
    """Base error for email report delivery problems."""


class EmailReportNotConfiguredError(EmailReportError):
    """Raised when the selected email provider is not configured."""


class EmailReportDeliveryError(EmailReportError):
    """Raised when the selected email provider rejects or fails a delivery."""


@dataclass(frozen=True)
class EmailReportContent:
    recipient: str
    share_text: str
    triage_label: str
    predicted_hemoglobin: float | None = None
    anemia_risk: float = 0.0


class EmailReportService:
    def configuration_issue(self) -> str | None:
        if self._provider == "resend":
            if not settings.resend_api_key:
                return "Resend is selected but ANEMIALENS_RESEND_API_KEY is missing."
            if not self._from_email:
                return "Resend is selected but ANEMIALENS_EMAIL_FROM_EMAIL is missing."
            return None

        if self._provider == "sendgrid":
            if not settings.sendgrid_api_key:
                return "SendGrid is selected but ANEMIALENS_SENDGRID_API_KEY is missing."
            if not self._from_email:
                return "SendGrid is selected but ANEMIALENS_EMAIL_FROM_EMAIL is missing."
            return None

        if self._provider == "gmail_api":
            missing: list[str] = []
            if not settings.gmail_client_id:
                missing.append("ANEMIALENS_GMAIL_CLIENT_ID")
            if not settings.gmail_client_secret:
                missing.append("ANEMIALENS_GMAIL_CLIENT_SECRET")
            if not settings.gmail_refresh_token:
                missing.append("ANEMIALENS_GMAIL_REFRESH_TOKEN")
            if not self._from_email:
                missing.append("ANEMIALENS_EMAIL_FROM_EMAIL")
            if missing:
                return f"Gmail API is selected but the following settings are missing: {', '.join(missing)}."
            return None

        missing: list[str] = []
        if not settings.smtp_username:
            missing.append("ANEMIALENS_SMTP_USERNAME")
        if not settings.smtp_password:
            missing.append("ANEMIALENS_SMTP_PASSWORD")
        if not self._from_email:
            missing.append("ANEMIALENS_EMAIL_FROM_EMAIL")
        if missing:
            detail = f"SMTP is selected but the following settings are missing: {', '.join(missing)}."
            if "ANEMIALENS_SMTP_PASSWORD" in missing and settings.smtp_host == "smtp.gmail.com":
                detail += " For Gmail SMTP, use a 16-character Google app password."
            return detail
        return None

    def is_configured(self) -> bool:
        return self.configuration_issue() is None

    def masked_recipient(self, recipient: str) -> str:
        local, _, domain = recipient.partition("@")
        if not local or not domain:
            return "***"
        if len(local) <= 2:
            return f"{local[0]}*@{domain}"
        return f"{local[:2]}***@{domain}"

    def send_report(self, payload: EmailReportContent) -> None:
        configuration_issue = self.configuration_issue()
        if configuration_issue is not None:
            raise EmailReportNotConfiguredError(configuration_issue)

        masked_recipient = self.masked_recipient(payload.recipient)
        log.info("[FIX] email report send started for %s", masked_recipient)

        try:
            if self._provider == "resend":
                self._send_via_resend(payload)
            elif self._provider == "sendgrid":
                self._send_via_sendgrid(payload)
            elif self._provider == "gmail_api":
                self._send_via_gmail_api(payload)
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
        parsed = urlsplit(f"{settings.resend_api_base.rstrip('/')}/emails")
        path = parsed.path or "/emails"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        body = json.dumps(self._build_resend_payload(payload)).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {settings.resend_api_key}",
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
            "Idempotency-Key": self._idempotency_key(payload),
            "User-Agent": "AnemiaLens/1.0 (+https://anemia-lens.vercel.app)",
        }
        connection_factory = (
            http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
        )
        try:
            connection = connection_factory(parsed.netloc, timeout=settings.smtp_timeout)
            try:
                connection.request("POST", path, body=body, headers=headers)
                response = connection.getresponse()
                raw = response.read().decode("utf-8", errors="replace")
            finally:
                connection.close()
        except OSError as exc:
            raise EmailReportDeliveryError(
                "Could not reach the configured email provider."
            ) from exc
        if response.status >= 400:
            detail = self._extract_provider_error(raw)
            raise EmailReportDeliveryError(
                f"Email provider rejected the request: {detail or f'HTTP {response.status}'}"
            )

    def _send_via_sendgrid(self, payload: EmailReportContent) -> None:
        parsed = urlsplit(f"{settings.sendgrid_api_base.rstrip('/')}/mail/send")
        path = parsed.path or "/mail/send"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        body = json.dumps(self._build_sendgrid_payload(payload)).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {settings.sendgrid_api_key}",
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
            "User-Agent": "AnemiaLens/1.0 (+https://anemia-lens.vercel.app)",
        }
        connection_factory = (
            http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
        )
        try:
            connection = connection_factory(parsed.netloc, timeout=settings.smtp_timeout)
            try:
                connection.request("POST", path, body=body, headers=headers)
                response = connection.getresponse()
                raw = response.read().decode("utf-8", errors="replace")
            finally:
                connection.close()
        except OSError as exc:
            raise EmailReportDeliveryError(
                "Could not reach the configured email provider."
            ) from exc
        if response.status >= 400:
            detail = self._extract_provider_error(raw)
            raise EmailReportDeliveryError(
                f"Email provider rejected the request: {detail or f'HTTP {response.status}'}"
            )

    def _send_via_gmail_api(self, payload: EmailReportContent) -> None:
        access_token = self._gmail_access_token()
        parsed = urlsplit(f"{settings.gmail_api_base.rstrip('/')}/users/me/messages/send")
        path = parsed.path or "/gmail/v1/users/me/messages/send"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        message = self._build_message(payload)
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        body = json.dumps({"raw": raw_message}).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
            "User-Agent": "AnemiaLens/1.0 (+https://anemia-lens.vercel.app)",
        }
        connection_factory = (
            http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
        )
        try:
            connection = connection_factory(parsed.netloc, timeout=settings.smtp_timeout)
            try:
                connection.request("POST", path, body=body, headers=headers)
                response = connection.getresponse()
                raw = response.read().decode("utf-8", errors="replace")
            finally:
                connection.close()
        except OSError as exc:
            raise EmailReportDeliveryError(
                "Could not reach the configured email provider."
            ) from exc
        if response.status >= 400:
            detail = self._extract_provider_error(raw)
            raise EmailReportDeliveryError(
                f"Email provider rejected the request: {detail or f'HTTP {response.status}'}"
            )

    def _gmail_access_token(self) -> str:
        parsed = urlsplit(settings.gmail_token_url)
        path = parsed.path or "/token"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        body = urlencode(
            {
                "client_id": settings.gmail_client_id,
                "client_secret": settings.gmail_client_secret,
                "refresh_token": settings.gmail_refresh_token,
                "grant_type": "refresh_token",
            }
        ).encode("utf-8")
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Content-Length": str(len(body)),
            "User-Agent": "AnemiaLens/1.0 (+https://anemia-lens.vercel.app)",
        }
        connection_factory = (
            http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
        )
        try:
            connection = connection_factory(parsed.netloc, timeout=settings.smtp_timeout)
            try:
                connection.request("POST", path, body=body, headers=headers)
                response = connection.getresponse()
                raw = response.read().decode("utf-8", errors="replace")
            finally:
                connection.close()
        except OSError as exc:
            raise EmailReportDeliveryError(
                "Could not reach Google's token endpoint."
            ) from exc
        if response.status >= 400:
            detail = self._extract_provider_error(raw)
            raise EmailReportDeliveryError(
                f"Gmail authorization failed: {detail or f'HTTP {response.status}'}"
            )
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise EmailReportDeliveryError("Gmail authorization returned an invalid response.") from exc
        access_token = data.get("access_token")
        if not isinstance(access_token, str) or not access_token.strip():
            raise EmailReportDeliveryError("Gmail authorization did not return an access token.")
        return access_token

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

    def _build_sendgrid_payload(self, payload: EmailReportContent) -> dict[str, object]:
        body: dict[str, object] = {
            "personalizations": [
                {
                    "to": [{"email": payload.recipient}],
                    "subject": self._subject(payload),
                }
            ],
            "from": {
                "email": self._from_email,
                "name": settings.email_from_name,
            },
            "content": [
                {"type": "text/plain", "value": self._build_plain_text(payload)},
                {"type": "text/html", "value": self._build_html(payload)},
            ],
        }
        if settings.email_reply_to:
            body["reply_to"] = {"email": settings.email_reply_to}
        return body

    def _idempotency_key(self, payload: EmailReportContent) -> str:
        safe_label = payload.triage_label.lower().replace(" ", "-")
        fingerprint = hashlib.sha256(
            "\n".join(
                [
                    payload.recipient.lower(),
                    payload.triage_label,
                    payload.share_text.strip(),
                    "" if payload.predicted_hemoglobin is None else f"{payload.predicted_hemoglobin:.3f}",
                    f"{payload.anemia_risk:.6f}",
                ]
            ).encode("utf-8")
        ).hexdigest()[:20]
        return f"email-report/{payload.recipient.lower()}/{safe_label}/{fingerprint}"[:256]

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
        next_steps = "\n".join(f"- {step}" for step in self._recommended_steps(payload))
        summary_line = self._email_result_story(payload)
        return (
            "AnemiaLens Screening Result Report\n"
            "================================\n\n"
            f"Triage Label: {payload.triage_label}\n"
            f"Anemia Risk Score: {risk_pct}%\n"
            f"{hb_line}\n\n"
            "Summary\n"
            "-------\n"
            f"{summary_line}\n\n"
            "Recommended Next Steps\n"
            "----------------------\n"
            f"{next_steps}\n\n"
            "Important\n"
            "---------\n"
            f"{SCREENING_DISCLAIMER} Please confirm results with a clinical blood test (CBC).\n\n"
            "AnemiaLens\n"
            "https://anemia-lens.vercel.app\n"
        )

    def _build_html(self, payload: EmailReportContent) -> str:
        hb_label, hb_value = self._hemoglobin_parts(payload.predicted_hemoglobin)
        risk_pct = round(payload.anemia_risk * 100)
        accent, accent_soft, accent_border, status_line = self._triage_theme(payload)
        summary_line = self._email_result_story(payload)
        detail_line = self._email_supporting_detail(payload)
        steps_html = "".join(
            f"""
            <tr>
              <td style="padding:0 0 10px 0;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                  <tr>
                    <td width="28" valign="top" style="padding-top:2px;">
                      <div style="width:18px;height:18px;border-radius:999px;background:{accent_soft};border:1px solid {accent_border};font-size:11px;line-height:18px;text-align:center;color:{accent};font-weight:700;">•</div>
                    </td>
                    <td style="font-size:14px;line-height:1.6;color:#1e293b;">
                      {escape(step)}
                    </td>
                  </tr>
                </table>
              </td>
            </tr>"""
            for step in self._recommended_steps(payload)
        )
        return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>AnemiaLens Screening Report</title>
  </head>
  <body style="margin:0;padding:0;background:#eef2f7;color:#0f172a;font-family:Arial,sans-serif;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#eef2f7;">
      <tr>
        <td align="center" style="padding:32px 16px;">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:640px;background:#ffffff;border:1px solid #dbe4ee;border-radius:24px;overflow:hidden;box-shadow:0 20px 60px rgba(15,23,42,0.08);">
            <tr>
              <td style="padding:28px 32px;background:#0f172a;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                  <tr>
                    <td align="left">
                      <div style="font-size:24px;font-weight:700;letter-spacing:-0.03em;color:#ffffff;">AnemiaLens</div>
                      <div style="margin-top:6px;font-size:13px;line-height:1.6;color:#94a3b8;">Smartphone-first screening summary, ready to review or share.</div>
                    </td>
                    <td align="right" valign="top">
                      <div style="display:inline-block;padding:8px 14px;border-radius:999px;font-size:11px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;background:{accent_soft};border:1px solid {accent_border};color:{accent};">
                        {escape(payload.triage_label)}
                      </div>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:28px 32px 12px 32px;">
                <div style="font-size:18px;font-weight:700;line-height:1.4;color:#0f172a;">{escape(status_line)}</div>
                <div style="margin-top:8px;font-size:14px;line-height:1.7;color:#475569;">
                  This email keeps the screening story short: what the result means, the estimated hemoglobin context, and what to do next.
                </div>
              </td>
            </tr>
            <tr>
              <td style="padding:8px 32px 0 32px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                  <tr>
                    <td width="50%" style="padding-right:8px;padding-bottom:16px;">
                      <div style="padding:18px;border:1px solid #dbe4ee;border-radius:18px;background:#f8fafc;">
                        <div style="font-size:11px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:#64748b;margin-bottom:8px;">Anemia Risk Score</div>
                        <div style="font-size:30px;font-weight:700;color:{accent};line-height:1;">{risk_pct}%</div>
                      </div>
                    </td>
                    <td width="50%" style="padding-left:8px;padding-bottom:16px;">
                      <div style="padding:18px;border:1px solid #dbe4ee;border-radius:18px;background:#f8fafc;">
                        <div style="font-size:11px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:#64748b;margin-bottom:8px;">{escape(hb_label)}</div>
                        <div style="font-size:24px;font-weight:700;color:#0f172a;line-height:1.2;">{escape(hb_value)}</div>
                      </div>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:8px 32px 0 32px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border:1px solid #dbe4ee;border-radius:18px;background:#ffffff;">
                  <tr>
                    <td style="padding:20px;">
                      <div style="font-size:11px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:#64748b;margin-bottom:10px;">Why this result</div>
                      <div style="font-size:15px;line-height:1.75;color:#1e293b;font-weight:600;margin-bottom:12px;">
                        {escape(summary_line)}
                      </div>
                      <div style="font-size:13px;line-height:1.7;color:#475569;">
                        {escape(detail_line)}
                      </div>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:18px 32px 0 32px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border:1px solid #dbe4ee;border-radius:18px;background:#f8fafc;">
                  <tr>
                    <td style="padding:20px 20px 8px 20px;">
                      <div style="font-size:11px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:#64748b;margin-bottom:10px;">Recommended next steps</div>
                    </td>
                  </tr>
                  {steps_html}
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:18px 32px 0 32px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#fff7ed;border:1px solid #fed7aa;border-radius:18px;">
                  <tr>
                    <td style="padding:18px 20px;font-size:13px;line-height:1.7;color:#7c2d12;">
                      <strong>Important:</strong> {escape(SCREENING_DISCLAIMER)} Please confirm results with a clinical blood test (CBC).
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:24px 32px 32px 32px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                  <tr>
                    <td align="left" style="font-size:12px;line-height:1.7;color:#64748b;">
                      Sent by AnemiaLens for quick review and clinician handoff.
                    </td>
                    <td align="right">
                      <a href="https://anemia-lens.vercel.app" style="display:inline-block;padding:12px 18px;border-radius:999px;background:#0f172a;color:#ffffff;text-decoration:none;font-size:13px;font-weight:700;">Open AnemiaLens</a>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""

    def _triage_theme(self, payload: EmailReportContent) -> tuple[str, str, str, str]:
        triage = payload.triage_label.lower()
        if "high" in triage:
            return (
                "#dc2626",
                "#fee2e2",
                "#fecaca",
                "High concern detected. Please prioritize follow-up quickly.",
            )
        if "moderate" in triage:
            return (
                "#d97706",
                "#fef3c7",
                "#fde68a",
                "Moderate risk detected. A clinical follow-up is worth arranging soon.",
            )
        if "uncertain" in triage:
            return (
                "#7c3aed",
                "#ede9fe",
                "#ddd6fe",
                "The scan was not strong enough for a confident call, so a retake is the safest next step.",
            )
        return (
            "#059669",
            "#dcfce7",
            "#bbf7d0",
            "No urgent concern was detected, but routine monitoring is still sensible.",
        )

    def _email_result_story(self, payload: EmailReportContent) -> str:
        triage = payload.triage_label.lower()
        if "high" in triage:
            return (
                "The screening found a strong low-hemoglobin pattern, so prompt clinical follow-up is the safest next step."
            )
        if "moderate" in triage:
            return (
                "The screening found a moderate low-hemoglobin pattern. It is not an emergency alert, but it is worth reviewing with a clinician soon."
            )
        if "uncertain" in triage:
            return (
                "The current image was not reliable enough for a confident screening call, so a cleaner retake or clinician review is safer than over-interpreting it."
            )
        return (
            "The screening did not show a strong urgent low-hemoglobin pattern, though routine monitoring remains sensible."
        )

    def _email_supporting_detail(self, payload: EmailReportContent) -> str:
        risk_pct = round(payload.anemia_risk * 100)
        if payload.predicted_hemoglobin is None:
            hb_detail = "The hemoglobin estimate was withheld because confidence was limited."
        else:
            hb_detail = f"The estimated hemoglobin for this run was {payload.predicted_hemoglobin:.1f} g/dL."
        return (
            f"This run produced a {risk_pct}% anemia-risk score. {hb_detail} Use the next steps below as a simple follow-up guide, not as a diagnosis."
        )

    def _recommended_steps(self, payload: EmailReportContent) -> list[str]:
        triage = payload.triage_label.lower()
        if "high" in triage:
            return [
                "Arrange a CBC blood test as soon as possible and avoid delaying clinical review.",
                "Share this summary with a clinician or family member who can help coordinate care.",
                "Seek urgent medical attention sooner if symptoms worsen or new warning signs appear.",
            ]
        if "moderate" in triage:
            return [
                "Book a follow-up with a healthcare provider within 1-2 weeks and discuss confirmatory blood work.",
                "Keep track of fatigue, dizziness, or shortness of breath if they continue.",
                "Consider a clearer retake if the original scan had quality warnings.",
            ]
        if "uncertain" in triage:
            return [
                "Retake the image in brighter, steadier lighting with the lower eyelid fully visible.",
                "Use this summary only as a retake reminder, not as a final decision.",
                "If symptoms are present, do not wait for a retake before speaking with a clinician.",
            ]
        return [
            "Maintain a balanced diet and monitor for any new or worsening symptoms.",
            "Repeat screening in 3-6 months or sooner if your health changes.",
            "Use this report as a simple summary if you want to discuss the result with a provider later.",
        ]

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
            error_obj = body.get("error")
            if isinstance(error_obj, dict):
                for key in ("message", "status"):
                    value = error_obj.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()
            errors = body.get("errors")
            if isinstance(errors, list):
                for item in errors:
                    if isinstance(item, dict):
                        value = item.get("message")
                        if isinstance(value, str) and value.strip():
                            return value.strip()
            for key in ("message", "error", "name"):
                value = body.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        stripped = raw_body.strip()
        return stripped or None
