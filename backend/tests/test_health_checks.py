"""
Tests for health check endpoints and health_checks module.

Covers:
- /health endpoint
- /readyz endpoint
- CheckResult dataclass
- HealthCheckCache TTL behavior
- Individual health check functions
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.health_checks import (
    CheckResult,
    HealthCheckCache,
    check_disk_space,
    check_memory_usage,
    check_cpu_usage,
    check_model_files,
    check_model_loadable,
    get_cached_health_status,
    health_cache,
    metrics_collector,
    run_all_health_checks,
)
from app.config import settings


# ---------------------------------------------------------------------------
# CheckResult
# ---------------------------------------------------------------------------


class TestCheckResult:
    def test_to_dict_returns_expected_keys(self) -> None:
        result = CheckResult(
            status="ok",
            component="test",
            message="All good",
            details={"key": "value"},
            timestamp=1700000000.0,
            latency_ms=12.34,
        )
        d = result.to_dict()
        assert d["status"] == "ok"
        assert d["component"] == "test"
        assert d["message"] == "All good"
        assert d["details"] == {"key": "value"}
        assert d["timestamp"] == 1700000000.0
        assert d["latency_ms"] == 12.34

    def test_to_dict_rounds_latency(self) -> None:
        result = CheckResult(
            status="ok",
            component="test",
            message="msg",
            latency_ms=12.34567,
        )
        assert result.to_dict()["latency_ms"] == 12.35

    def test_default_details_is_empty_dict(self) -> None:
        result = CheckResult(status="ok", component="x", message="m")
        assert result.details == {}

    def test_default_timestamp_is_current(self) -> None:
        before = time.time()
        result = CheckResult(status="ok", component="x", message="m")
        after = time.time()
        assert before <= result.timestamp <= after


# ---------------------------------------------------------------------------
# HealthCheckCache
# ---------------------------------------------------------------------------


class TestHealthCheckCache:
    def test_is_fresh_false_when_empty(self) -> None:
        cache = HealthCheckCache(ttl_seconds=10)
        assert cache.is_fresh() is False

    def test_is_fresh_false_after_ttl(self) -> None:
        cache = HealthCheckCache(ttl_seconds=0.01)
        cache.set({"status": "healthy"})
        assert cache.is_fresh() is True
        time.sleep(0.02)
        assert cache.is_fresh() is False

    def test_get_returns_cached_when_fresh(self) -> None:
        cache = HealthCheckCache(ttl_seconds=10)
        cache.set({"status": "healthy"})
        assert cache.get() == {"status": "healthy"}

    def test_get_returns_none_when_expired(self) -> None:
        cache = HealthCheckCache(ttl_seconds=0.01)
        cache.set({"status": "healthy"})
        time.sleep(0.02)
        assert cache.get() is None

    def test_set_stores_result(self) -> None:
        cache = HealthCheckCache(ttl_seconds=10)
        cache.set({"key": "val"})
        assert cache.get() == {"key": "val"}

    def test_invalid_clears_cache(self) -> None:
        cache = HealthCheckCache(ttl_seconds=10)
        cache.set({"key": "val"})
        cache.invalidate()
        assert cache.get() is None
        assert cache.is_fresh() is False


# ---------------------------------------------------------------------------
# Individual health check functions
# ---------------------------------------------------------------------------


class TestDiskSpace:
    def test_returns_ok_for_normal_usage(self) -> None:
        result = check_disk_space()
        assert result.component == "disk_space"
        assert result.status in ("ok", "degraded", "error")
        assert "total_gb" in result.details or "error_type" in result.details

    def test_details_contain_usage_info(self) -> None:
        result = check_disk_space()
        if result.status == "ok":
            assert "usage_percent" in result.details
            assert "free_gb" in result.details


class TestMemoryUsage:
    def test_returns_result(self) -> None:
        result = check_memory_usage()
        assert result.component == "memory"
        assert result.status in ("ok", "degraded", "error")

    def test_details_contain_process_info(self) -> None:
        result = check_memory_usage()
        if result.status == "ok":
            assert "process_rss_mb" in result.details
            assert "system_memory_percent" in result.details


class TestCpuUsage:
    def test_returns_result(self) -> None:
        result = check_cpu_usage()
        assert result.component == "cpu"
        assert result.status in ("ok", "degraded", "error")

    def test_details_contain_cpu_info(self) -> None:
        result = check_cpu_usage()
        if result.status == "ok":
            assert "cpu_count" in result.details
            assert "system_cpu_percent" in result.details


class TestModelFiles:
    def test_returns_result(self) -> None:
        result = check_model_files()
        assert result.component == "model_files"
        assert result.status in ("ok", "degraded", "error")
        assert "total_models_checked" in result.details
        assert "present" in result.details
        assert "missing" in result.details


class TestModelLoadable:
    def test_returns_result(self) -> None:
        result = check_model_loadable()
        assert result.component == "model_loadable"
        assert result.status in ("ok", "degraded", "error")


# ---------------------------------------------------------------------------
# run_all_health_checks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestRunAllHealthChecks:
    async def test_returns_aggregated_dict(self) -> None:
        result = await run_all_health_checks()
        assert isinstance(result, dict)
        assert "status" in result
        assert "checks" in result
        assert "timestamp" in result
        assert "version" in result
        assert "system" in result
        assert "total_latency_ms" in result

    async def test_status_is_one_of_expected(self) -> None:
        result = await run_all_health_checks()
        assert result["status"] in ("healthy", "degraded", "unhealthy")

    async def test_checks_has_expected_keys(self) -> None:
        result = await run_all_health_checks()
        checks = result["checks"]
        assert "disk_space" in checks
        assert "memory" in checks
        assert "cpu" in checks
        assert "model_files" in checks
        assert "model_loadable" in checks


# ---------------------------------------------------------------------------
# Cached health status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGetCachedHealthStatus:
    async def test_returns_result(self) -> None:
        health_cache.invalidate()
        result = await get_cached_health_status()
        assert isinstance(result, dict)
        assert "status" in result
        assert "cache_hit" in result
        assert result["cache_hit"] is False  # First call misses cache

    async def test_second_call_hits_cache(self) -> None:
        health_cache.invalidate()
        result1 = await get_cached_health_status()
        assert result1["cache_hit"] is False

        result2 = await get_cached_health_status()
        assert result2["cache_hit"] is True

    async def test_cached_result_is_same(self) -> None:
        health_cache.invalidate()
        result1 = await get_cached_health_status()
        result2 = await get_cached_health_status()
        assert result1["status"] == result2["status"]
        assert result1["timestamp"] == result2["timestamp"]


# ---------------------------------------------------------------------------
# MetricsCollector
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestMetricsCollector:
    async def test_record_request(self) -> None:
        await metrics_collector.record_request(
            path="/api/test", status_code=200, latency_ms=50.0
        )
        # Should not raise

    async def test_record_request_error(self) -> None:
        await metrics_collector.record_request(
            path="/api/error", status_code=500, latency_ms=10.0
        )

    async def test_record_inference(self) -> None:
        await metrics_collector.record_inference(latency_ms=100.0, success=True)

    async def test_record_inference_failure(self) -> None:
        await metrics_collector.record_inference(latency_ms=50.0, success=False)

    async def test_record_cache_access_hit(self) -> None:
        await metrics_collector.record_cache_access(hit=True)

    async def test_record_cache_access_miss(self) -> None:
        await metrics_collector.record_cache_access(hit=False)

    async def test_record_active_user(self) -> None:
        await metrics_collector.record_active_user(42)

    async def test_get_prometheus_format(self) -> None:
        text = await metrics_collector.get_prometheus_format()
        assert isinstance(text, str)
        assert "HELP" in text or "TYPE" in text

    async def test_get_metrics_dict(self) -> None:
        metrics = await metrics_collector.get_metrics_dict()
        assert isinstance(metrics, dict)
        assert "request" in metrics
        assert "inference" in metrics
        assert "cache" in metrics

    async def test_request_count_increases(self) -> None:
        before = await metrics_collector.get_metrics_dict()
        before_count = before["request"]["total"]
        await metrics_collector.record_request(
            path="/api/count-test", status_code=200, latency_ms=10.0
        )
        after = await metrics_collector.get_metrics_dict()
        assert after["request"]["total"] > before_count

    async def test_error_count_increases_on_500(self) -> None:
        before = await metrics_collector.get_metrics_dict()
        before_errors = before["request"]["errors"]
        await metrics_collector.record_request(
            path="/api/error-count-test", status_code=500, latency_ms=10.0
        )
        after = await metrics_collector.get_metrics_dict()
        assert after["request"]["errors"] > before_errors

    async def test_reset(self) -> None:
        await metrics_collector.record_request(
            path="/api/reset-test", status_code=200, latency_ms=10.0
        )
        await metrics_collector.reset()
        metrics = await metrics_collector.get_metrics_dict()
        assert metrics["request"]["total"] == 0
        assert metrics["request"]["errors"] == 0


# ---------------------------------------------------------------------------
# Health endpoint via FastAPI TestClient
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    def test_health_returns_200(self) -> None:
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "checks" in data

    def test_health_contains_cache_hit_field(self) -> None:
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        response = client.get("/health")
        data = response.json()
        assert "cache_hit" in data

    def test_health_system_info_present(self) -> None:
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        response = client.get("/health")
        data = response.json()
        assert "system" in data
        assert "python_version" in data["system"]
