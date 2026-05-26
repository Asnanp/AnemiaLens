from __future__ import annotations

import json
import time
from pathlib import Path

from pydantic import ValidationError

from app.config import settings
from app.schemas import PatientProfileInput, SymptomInput


class InvalidRequestPayload(ValueError):
    pass


#region agent log
def _agent_debug_log(run_id: str, hypothesis_id: str, location: str, message: str, data: dict) -> None:
    pass  # Debug instrumentation disabled for production
#endregion


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
        removed_legacy_symptoms = "symptoms" in payload
        if removed_legacy_symptoms:
            payload = dict(payload)
            payload.pop("symptoms", None)
        #region agent log
        _agent_debug_log(
            "run14",
            "H30",
            "backend/app/services/request_parsing.py:parse_patient_profile:payload",
            "Patient profile payload normalized",
            {
                "hadLegacySymptomsField": removed_legacy_symptoms,
                "keys": sorted(payload.keys()),
            },
        )
        #endregion
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
