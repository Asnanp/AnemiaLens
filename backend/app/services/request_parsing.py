from __future__ import annotations

import json

from pydantic import ValidationError

from app.config import settings
from app.schemas import PatientProfileInput, SymptomInput


class InvalidRequestPayload(ValueError):
    pass


def parse_symptoms(raw: str | None) -> SymptomInput:
    if not raw:
        return SymptomInput()

    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise InvalidRequestPayload("Invalid symptoms payload: expected a JSON object.")
        return SymptomInput.model_validate(payload)
    except InvalidRequestPayload:
        raise
    except (TypeError, json.JSONDecodeError, ValidationError) as exc:
        detail = _validation_detail(exc)
        if detail:
            raise InvalidRequestPayload(f"Invalid symptoms payload: {detail}") from exc
        raise InvalidRequestPayload("Invalid symptoms payload.") from exc


def parse_patient_profile(raw: str | None) -> PatientProfileInput:
    if not raw:
        return PatientProfileInput()

    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise InvalidRequestPayload("Invalid patient profile payload: expected a JSON object.")
        return PatientProfileInput.model_validate(payload)
    except InvalidRequestPayload:
        raise
    except (TypeError, json.JSONDecodeError, ValidationError) as exc:
        detail = _validation_detail(exc)
        if detail:
            raise InvalidRequestPayload(f"Invalid patient profile payload: {detail}") from exc
        raise InvalidRequestPayload("Invalid patient profile payload.") from exc


def normalize_optional_text(
    value: str | None,
    *,
    field_name: str,
    max_length: int | None = None,
) -> str | None:
    if value is None:
        return None

    normalized = " ".join(value.split())
    if not normalized:
        return None

    limit = settings.max_field_length if max_length is None else max_length
    if len(normalized) > limit:
        raise InvalidRequestPayload(f"{field_name} must be {limit} characters or fewer.")

    return normalized


def _validation_detail(exc: Exception) -> str | None:
    if isinstance(exc, ValidationError):
        errors = exc.errors()
        if errors:
            first = errors[0]
            location = ".".join(str(part) for part in first.get("loc", ()) if part is not None)
            message = str(first.get("msg", "")).strip()
            if location and message:
                return f"{location}: {message}"
            if location:
                return location
            if message:
                return message
    elif isinstance(exc, json.JSONDecodeError):
        return "malformed JSON"
    return None
