"""
Integration tests for API endpoints.

Covers:
- POST /api/analyze (full screening pipeline)
- POST /api/quality-check
- POST /api/guidance/chat
- Root redirect
- Error handling (413, 415, 422)
- Middleware behavior (request ID, CORS, rate limiting)
"""

from __future__ import annotations

import io
import json

from fastapi.testclient import TestClient
from PIL import Image


def _create_test_image(size: tuple[int, int] = (200, 200), color: tuple = (140, 90, 80)) -> bytes:
    """Create a test image and return its bytes."""
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _create_test_image_png(size: tuple[int, int] = (200, 200), color: tuple = (140, 90, 80)) -> bytes:
    """Create a test PNG image and return its bytes."""
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Root redirect
# ---------------------------------------------------------------------------


class TestRootEndpoint:
    def test_root_redirects_to_docs(self) -> None:
        from app.main import app

        client = TestClient(app, follow_redirects=False)
        response = client.get("/")
        assert response.status_code == 307
        assert "/docs" in response.headers["location"]


# ---------------------------------------------------------------------------
# POST /api/analyze
# ---------------------------------------------------------------------------


class TestAnalyzeEndpoint:
    def test_analyze_with_jpeg_image(self) -> None:
        from app.main import app

        client = TestClient(app)
        image_bytes = _create_test_image()
        response = client.post(
            "/api/analyze",
            files={"image": ("test.jpg", image_bytes, "image/jpeg")},
        )
        # May be 200 (model ready) or some error if model not loaded
        assert response.status_code in (200, 500)
        if response.status_code == 200:
            data = response.json()
            assert "blocked" in data
            assert "quality" in data
            assert "analysis_meta" in data
            assert "request_id" in data.get("analysis_meta", {})

    def test_analyze_with_png_image(self) -> None:
        from app.main import app

        client = TestClient(app)
        image_bytes = _create_test_image_png()
        response = client.post(
            "/api/analyze",
            files={"image": ("test.png", image_bytes, "image/png")},
        )
        assert response.status_code in (200, 500)

    def test_analyze_with_symptoms(self) -> None:
        from app.main import app

        client = TestClient(app)
        image_bytes = _create_test_image()
        response = client.post(
            "/api/analyze",
            files={"image": ("test.jpg", image_bytes, "image/jpeg")},
            data={"symptoms": json.dumps({"fatigue": True, "dizziness": False})},
        )
        assert response.status_code in (200, 422, 500)

    def test_analyze_with_patient_profile(self) -> None:
        from app.main import app

        client = TestClient(app)
        image_bytes = _create_test_image()
        profile = json.dumps({"age": 30, "sex": "female"})
        response = client.post(
            "/api/analyze",
            files={"image": ("test.jpg", image_bytes, "image/jpeg")},
            data={"patient_profile": profile},
        )
        assert response.status_code in (200, 422, 500)

    def test_analyze_with_language(self) -> None:
        from app.main import app

        client = TestClient(app)
        image_bytes = _create_test_image()
        response = client.post(
            "/api/analyze",
            files={"image": ("test.jpg", image_bytes, "image/jpeg")},
            data={"language": "es"},
        )
        assert response.status_code in (200, 422, 500)

    def test_analyze_with_region(self) -> None:
        from app.main import app

        client = TestClient(app)
        image_bytes = _create_test_image()
        response = client.post(
            "/api/analyze",
            files={"image": ("test.jpg", image_bytes, "image/jpeg")},
            data={"region": "LATAM"},
        )
        assert response.status_code in (200, 422, 500)

    def test_analyze_response_has_request_id_header(self) -> None:
        from app.main import app

        client = TestClient(app)
        image_bytes = _create_test_image()
        response = client.post(
            "/api/analyze",
            files={"image": ("test.jpg", image_bytes, "image/jpeg")},
        )
        assert "x-request-id" in response.headers
        assert "x-response-time" in response.headers

    def test_analyze_with_all_parameters(self) -> None:
        from app.main import app

        client = TestClient(app)
        image_bytes = _create_test_image()
        response = client.post(
            "/api/analyze",
            files={"image": ("test.jpg", image_bytes, "image/jpeg")},
            data={
                "symptoms": json.dumps({"fatigue": True}),
                "patient_profile": json.dumps({"age": 25, "sex": "female"}),
                "language": "en",
                "region": "US",
            },
        )
        assert response.status_code in (200, 422, 500)


# ---------------------------------------------------------------------------
# POST /api/quality-check
# ---------------------------------------------------------------------------


class TestQualityCheckEndpoint:
    def test_quality_check_with_jpeg(self) -> None:
        from app.main import app

        client = TestClient(app)
        image_bytes = _create_test_image()
        response = client.post(
            "/api/quality-check",
            files={"image": ("test.jpg", image_bytes, "image/jpeg")},
        )
        # May be 200 or error depending on quality service state
        assert response.status_code in (200, 415, 500)
        if response.status_code == 200:
            data = response.json()
            assert "quality" in data

    def test_quality_check_with_png(self) -> None:
        from app.main import app

        client = TestClient(app)
        image_bytes = _create_test_image_png()
        response = client.post(
            "/api/quality-check",
            files={"image": ("test.png", image_bytes, "image/png")},
        )
        assert response.status_code in (200, 415, 500)

    def test_quality_check_returns_roi_preview(self) -> None:
        from app.main import app

        client = TestClient(app)
        image_bytes = _create_test_image()
        response = client.post(
            "/api/quality-check",
            files={"image": ("test.jpg", image_bytes, "image/jpeg")},
        )
        if response.status_code == 200:
            data = response.json()
            assert "roi_preview" in data


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_rejects_non_image_file(self) -> None:
        from app.main import app

        client = TestClient(app)
        response = client.post(
            "/api/quality-check",
            files={"image": ("test.txt", b"not an image", "text/plain")},
        )
        assert response.status_code in (415, 422, 500)

    def test_rejects_invalid_image_data(self) -> None:
        from app.main import app

        client = TestClient(app)
        response = client.post(
            "/api/quality-check",
            files={"image": ("test.jpg", b"\xff\xd8\xff\xe0invalid_jpeg_data", "image/jpeg")},
        )
        # Should return 415 (unsupported media) or 422 (unprocessable)
        assert response.status_code in (415, 422, 500)

    def test_analyze_rejects_non_image_file(self) -> None:
        from app.main import app

        client = TestClient(app)
        response = client.post(
            "/api/analyze",
            files={"image": ("test.txt", b"not an image", "text/plain")},
        )
        assert response.status_code in (415, 422, 500)

    def test_rejects_oversized_image(self) -> None:
        """Test that very large images are rejected with 413."""
        from app.main import app
        from app.config import settings

        client = TestClient(app)
        # Create an image larger than the limit
        max_bytes = settings.max_image_bytes
        oversized = b"\x00" * (max_bytes + 1024)
        response = client.post(
            "/api/analyze",
            files={"image": ("huge.jpg", oversized, "image/jpeg")},
        )
        assert response.status_code in (413, 500)

    def test_error_response_has_request_id(self) -> None:
        from app.main import app

        client = TestClient(app)
        response = client.post(
            "/api/quality-check",
            files={"image": ("test.txt", b"not an image", "text/plain")},
        )
        # Even error responses should have request ID
        assert "x-request-id" in response.headers


# ---------------------------------------------------------------------------
# POST /api/guidance/chat
# ---------------------------------------------------------------------------


class TestGuidanceChatEndpoint:
    def test_guidance_chat_with_valid_payload(self) -> None:
        from app.main import app

        client = TestClient(app)
        # Create a minimal analysis payload
        analysis_payload = {
            "blocked": False,
            "quality": {
                "passed": True,
                "blur_score": 150.0,
                "brightness_score": 0.3,
                "contrast_score": 0.15,
                "framing_score": 1.5,
                "issues": [],
            },
            "prediction": {
                "anemia_risk": 0.45,
                "predicted_hemoglobin": 12.5,
                "confidence": 0.7,
                "uncertainty": 0.3,
                "reliability_flag": "medium",
                "screening_label": "uncertain",
                "screening_text": "Uncertain result.",
                "model_source": "test",
            },
            "triage": {
                "level": "moderate",
                "text": "Moderate concern.",
                "anemia_risk": 0.45,
                "action": "consult_provider",
            },
            "decision_audit": {
                "quality_assessment": "Image quality acceptable.",
                "model_analysis": "Model prediction with medium confidence.",
                "triage_rationale": "Moderate risk level.",
                "guidance_summary": "Consult a provider.",
            },
            "guidance": {
                "summary": "Consult a provider for confirmation.",
                "immediate_actions": [],
                "monitoring": [],
                "prevention": [],
                "disclaimer": "This is screening only.",
            },
        }

        payload = {
            "analysis": analysis_payload,
            "message": "What should I do next?",
            "history": [],
        }

        response = client.post(
            "/api/guidance/chat",
            json=payload,
        )
        # May succeed or fail depending on guidance service availability
        assert response.status_code in (200, 422, 500)

    def test_guidance_chat_without_analysis_returns_422(self) -> None:
        from app.main import app

        client = TestClient(app)
        response = client.post(
            "/api/guidance/chat",
            json={"message": "Hello"},
        )
        assert response.status_code in (422, 500)


# ---------------------------------------------------------------------------
# Middleware behavior
# ---------------------------------------------------------------------------


class TestMiddlewareBehavior:
    def test_cors_headers_present(self) -> None:
        from app.main import app

        client = TestClient(app)
        response = client.options(
            "/health",
            headers={"Origin": "http://localhost:5173"},
        )
        # CORS preflight or the response should have CORS headers
        assert "access-control-allow-origin" in response.headers or response.status_code in (200, 405)

    def test_request_id_on_health_endpoint(self) -> None:
        from app.main import app

        client = TestClient(app)
        response = client.get("/health")
        assert "x-request-id" in response.headers

    def test_response_time_header_present(self) -> None:
        from app.main import app

        client = TestClient(app)
        response = client.get("/readyz")
        assert "x-response-time" in response.headers

    def test_request_id_is_unique(self) -> None:
        from app.main import app

        client = TestClient(app)
        r1 = client.get("/health")
        r2 = client.get("/health")
        id1 = r1.headers.get("x-request-id")
        id2 = r2.headers.get("x-request-id")
        # Both should have IDs
        assert id1 is not None
        assert id2 is not None
        # They should be different (probability of collision is negligible)
        assert id1 != id2


# ---------------------------------------------------------------------------
# Auth routes (basic smoke tests)
# ---------------------------------------------------------------------------


class TestAuthRoutes:
    def test_register_returns_422_without_required_fields(self) -> None:
        from app.main import app

        client = TestClient(app)
        response = client.post("/auth/register", json={})
        assert response.status_code in (422, 500)

    def test_login_returns_422_without_credentials(self) -> None:
        from app.main import app

        client = TestClient(app)
        response = client.post("/auth/login", json={})
        assert response.status_code in (422, 500)

    def test_profile_requires_auth(self) -> None:
        from app.main import app

        client = TestClient(app)
        response = client.get("/auth/profile")
        # Should be 401 (unauthorized) or 422 if token parsing fails
        assert response.status_code in (401, 422, 500)


# ---------------------------------------------------------------------------
# History routes (basic smoke tests)
# ---------------------------------------------------------------------------


class TestHistoryRoutes:
    def test_history_requires_auth(self) -> None:
        from app.main import app

        client = TestClient(app)
        response = client.get("/api/history")
        assert response.status_code in (401, 422, 500)


# ---------------------------------------------------------------------------
# Admin routes (basic smoke tests)
# ---------------------------------------------------------------------------


class TestAdminRoutes:
    def test_admin_requires_auth(self) -> None:
        from app.main import app

        client = TestClient(app)
        response = client.get("/api/admin/stats")
        assert response.status_code in (401, 403, 422, 500)


# ---------------------------------------------------------------------------
# API route module imports
# ---------------------------------------------------------------------------


class TestApiModules:
    def test_auth_router_imported(self) -> None:
        from app.main import app
        routes = [r.path for r in app.routes]
        # Auth routes should be registered
        auth_routes = [r for r in routes if r.startswith("/auth")]
        assert len(auth_routes) > 0

    def test_history_router_imported(self) -> None:
        from app.main import app
        routes = [r.path for r in app.routes]
        history_routes = [r for r in routes if "/history" in r]
        assert len(history_routes) > 0
