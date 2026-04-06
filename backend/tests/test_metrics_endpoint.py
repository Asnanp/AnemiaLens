"""
Tests for the /metrics endpoint.

Covers:
- Prometheus text format output
- Content type
- Response structure
"""

from __future__ import annotations

from fastapi.testclient import TestClient


class TestMetricsEndpoint:
    def test_metrics_returns_200(self) -> None:
        from app.main import app

        client = TestClient(app)
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_content_type(self) -> None:
        from app.main import app

        client = TestClient(app)
        response = client.get("/metrics")
        content_type = response.headers.get("content-type", "")
        assert "text/plain" in content_type

    def test_metrics_body_is_non_empty_text(self) -> None:
        from app.main import app

        client = TestClient(app)
        response = client.get("/metrics")
        body = response.text
        assert len(body) > 0
        assert isinstance(body, str)

    def test_metrics_contains_prometheus_directives(self) -> None:
        from app.main import app

        client = TestClient(app)
        response = client.get("/metrics")
        body = response.text
        # Prometheus format requires at least HELP or TYPE directives
        assert "HELP" in body or "TYPE" in body

    def test_metrics_includes_request_metrics(self) -> None:
        from app.main import app

        client = TestClient(app)
        # First make some requests
        client.get("/readyz")
        response = client.get("/metrics")
        body = response.text
        assert "request" in body.lower() or "http" in body.lower()

    def test_metrics_includes_inference_metrics(self) -> None:
        from app.main import app

        client = TestClient(app)
        response = client.get("/metrics")
        body = response.text
        assert "inference" in body.lower() or "model" in body.lower()

    def test_metrics_includes_cache_metrics(self) -> None:
        from app.main import app

        client = TestClient(app)
        response = client.get("/metrics")
        body = response.text
        assert "cache" in body.lower()

    def test_metrics_idempotent(self) -> None:
        from app.main import app

        client = TestClient(app)
        r1 = client.get("/metrics")
        r2 = client.get("/metrics")
        assert r1.status_code == r2.status_code == 200


class TestReadyzEndpoint:
    def test_readyz_returns_200_when_ready(self) -> None:
        from app.main import app

        client = TestClient(app)
        response = client.get("/readyz")
        assert response.status_code in (200, 503)

    def test_readyz_contains_status_field(self) -> None:
        from app.main import app

        client = TestClient(app)
        response = client.get("/readyz")
        data = response.json()
        assert "status" in data
        assert data["status"] in ("ready", "degraded")

    def test_readyz_contains_model_ready_field(self) -> None:
        from app.main import app

        client = TestClient(app)
        response = client.get("/readyz")
        data = response.json()
        assert "model_ready" in data

    def test_readyz_contains_guidance_status(self) -> None:
        from app.main import app

        client = TestClient(app)
        response = client.get("/readyz")
        data = response.json()
        assert "guidance_client_ready" in data
        assert "guidance_strategy" in data


class TestRuntimeStatusEndpoint:
    def test_runtime_status_returns_200(self) -> None:
        from app.main import app

        client = TestClient(app)
        response = client.get("/api/runtime-status")
        assert response.status_code == 200

    def test_runtime_status_has_model_info(self) -> None:
        from app.main import app

        client = TestClient(app)
        response = client.get("/api/runtime-status")
        data = response.json()
        assert "model" in data

    def test_runtime_status_has_guidance_info(self) -> None:
        from app.main import app

        client = TestClient(app)
        response = client.get("/api/runtime-status")
        data = response.json()
        assert "guidance" in data
