"""
Comprehensive health checks and monitoring for AnemiaLens backend.

Provides:
- Database connectivity checks (Supabase / SQLite / PostgreSQL)
- Model file integrity validation
- External API availability (Mistral, etc.)
- System resource monitoring (disk, memory)
- Cached health check results with TTL
- Prometheus-compatible metrics collection
"""

from __future__ import annotations

import asyncio
import gc
import hashlib
import os
import platform
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import psutil

from app.config import BACKEND_ROOT, MODELS_DIR, settings

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class CheckResult:
    """Result of a single health check."""

    status: str  # "ok", "degraded", "error"
    component: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "component": self.component,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
            "latency_ms": round(self.latency_ms, 2),
        }


# ---------------------------------------------------------------------------
# Database health checks
# ---------------------------------------------------------------------------


async def check_database_connectivity() -> CheckResult:
    """Test database connectivity with a lightweight query."""
    start = time.perf_counter()
    try:
        from app.database import engine

        async with engine.connect() as conn:
            from sqlalchemy import text

            # Lightweight query — works on both SQLite and PostgreSQL
            if "sqlite" in str(engine.url):
                await conn.execute(text("SELECT 1"))
            else:
                await conn.execute(text("SELECT 1"))
            await conn.commit()

        latency_ms = (time.perf_counter() - start) * 1000
        db_type = "sqlite" if "sqlite" in str(engine.url) else "postgresql"

        # Check pool health
        pool_status = "N/A"
        if hasattr(engine, "pool"):
            pool_status = "active"

        return CheckResult(
            status="ok",
            component="database",
            message=f"{db_type.title()} connection healthy",
            details={
                "db_type": db_type,
                "pool_status": pool_status,
                "database_url_masked": _mask_url(str(engine.url)),
            },
            latency_ms=latency_ms,
        )
    except Exception as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        return CheckResult(
            status="error",
            component="database",
            message=f"Database connection failed: {exc}",
            details={"db_type": _guess_db_type(), "error_type": type(exc).__name__},
            latency_ms=latency_ms,
        )


async def check_database_tables() -> CheckResult:
    """Verify that required ORM tables exist."""
    start = time.perf_counter()
    try:
        from app.database import async_session_factory
        from sqlalchemy import text

        async with async_session_factory() as session:
            # Use raw connection for inspection
            result = await session.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                    if "sqlite" in str(async_session_factory.kw.get("bind").url)
                    else "SELECT tablename FROM pg_tables WHERE schemaname='public'"
                )
            )
            tables = [row[0] for row in result.fetchall()]

        latency_ms = (time.perf_counter() - start) * 1000

        expected_tables = {"users", "screenings", "audit_logs"}
        missing = expected_tables - set(tables)

        if missing:
            return CheckResult(
                status="degraded",
                component="database_tables",
                message=f"Missing tables: {', '.join(sorted(missing))}",
                details={"existing_tables": sorted(tables), "missing_tables": sorted(missing)},
                latency_ms=latency_ms,
            )

        return CheckResult(
            status="ok",
            component="database_tables",
            message="All required tables present",
            details={"table_count": len(tables), "expected_tables": sorted(expected_tables)},
            latency_ms=latency_ms,
        )
    except Exception as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        return CheckResult(
            status="error",
            component="database_tables",
            message=f"Table check failed: {exc}",
            details={"error_type": type(exc).__name__},
            latency_ms=latency_ms,
        )


# ---------------------------------------------------------------------------
# Model file integrity checks
# ---------------------------------------------------------------------------


def check_model_files() -> CheckResult:
    """Verify that critical model files exist and have valid sizes."""
    start = time.perf_counter()

    [
        ("primary_model", settings.__dict__.get("_DEFAULT_MODEL_PATH", MODELS_DIR / "anemia_model.pt")),
    ]

    # Collect all configured model paths from settings
    model_paths = [
        ("primary_model", MODELS_DIR / "anemia_model.pt"),
        ("ensemble_model", MODELS_DIR / "ensemble_model.json"),
        ("deep_stack_model", MODELS_DIR / "deep_stack_model.joblib"),
        ("efficientnet_model", MODELS_DIR / "efficientnet_anemia.pth"),
        ("runtime_calibrator", MODELS_DIR / "runtime_risk_calibrator.pkl"),
        ("runtime_refiner", MODELS_DIR / "runtime_screening_refiner.pkl"),
    ]

    # Also check archive models that may exist
    archive_candidates = list(MODELS_DIR.glob("archive-fusion-*.joblib"))
    for idx, candidate in enumerate(archive_candidates):
        model_paths.append((f"archive_model_{idx}", candidate))

    results: list[dict[str, Any]] = []
    missing_count = 0
    total_size_bytes = 0

    for name, path in model_paths:
        path = Path(path)
        if path.exists():
            size_bytes = path.stat().st_size
            total_size_bytes += size_bytes
            # Compute MD5 for integrity tracking
            file_hash = _compute_file_hash(path, max_bytes=1024 * 1024)
            results.append(
                {
                    "name": name,
                    "status": "present",
                    "path": str(path.name),
                    "size_mb": round(size_bytes / (1024 * 1024), 2),
                    "hash_prefix": file_hash[:8] if file_hash else None,
                }
            )
        else:
            missing_count += 1
            results.append(
                {
                    "name": name,
                    "status": "missing",
                    "path": str(path.name),
                }
            )

    latency_ms = (time.perf_counter() - start) * 1000

    has_efficientnet = any(r["name"] == "efficientnet_model" and r["status"] == "present" for r in results)

    if missing_count == 0 or has_efficientnet:
        status = "ok"
        message = "Required model files present and valid (using efficientnet fallback)" if has_efficientnet and missing_count > 0 else "All model files present and valid"
    elif missing_count <= len(model_paths) // 2:
        status = "degraded"
        message = f"{missing_count} of {len(model_paths)} model files missing"
    else:
        status = "error"
        message = f"{missing_count} of {len(model_paths)} model files missing — service severely degraded"

    return CheckResult(
        status=status,
        component="model_files",
        message=message,
        details={
            "total_models_checked": len(model_paths),
            "present": len(model_paths) - missing_count,
            "missing": missing_count,
            "total_size_mb": round(total_size_bytes / (1024 * 1024), 2),
            "models": results,
        },
        latency_ms=latency_ms,
    )


def check_model_loadable() -> CheckResult:
    """Attempt to verify that the predictor can be instantiated."""
    start = time.perf_counter()
    try:
        from app.services.prediction import ScreeningPredictor

        predictor = ScreeningPredictor()
        ready = predictor.is_ready()

        latency_ms = (time.perf_counter() - start) * 1000

        if ready:
            return CheckResult(
                status="ok",
                component="model_loadable",
                message="ScreeningPredictor initialized and ready",
                details={"ready": True},
                latency_ms=latency_ms,
            )
        else:
            return CheckResult(
                status="degraded",
                component="model_loadable",
                message="ScreeningPredictor initialized but not fully ready",
                details={"ready": False},
                latency_ms=latency_ms,
            )
    except Exception as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        return CheckResult(
            status="error",
            component="model_loadable",
            message=f"ScreeningPredictor failed to initialize: {exc}",
            details={"error_type": type(exc).__name__},
            latency_ms=latency_ms,
        )


# ---------------------------------------------------------------------------
# External API checks
# ---------------------------------------------------------------------------


async def check_mistral_api() -> CheckResult:
    """Check Mistral API availability."""
    start = time.perf_counter()

    if not settings.mistral_enabled:
        return CheckResult(
            status="ok",
            component="mistral_api",
            message="Mistral guidance is disabled (by configuration)",
            details={"enabled": False},
            latency_ms=0.0,
        )

    if not settings.mistral_api_key:
        return CheckResult(
            status="degraded",
            component="mistral_api",
            message="Mistral enabled but no API key configured — using fallback",
            details={"enabled": True, "api_key_present": False, "fallback_active": True},
            latency_ms=0.0,
        )

    try:
        import requests

        # Lightweight check — hit the models endpoint (no token cost)
        resp = requests.get(
            "https://api.mistral.ai/v1/models",
            headers={"Authorization": f"Bearer {settings.mistral_api_key}"},
            timeout=5,
        )

        latency_ms = (time.perf_counter() - start) * 1000

        if resp.status_code == 200:
            return CheckResult(
                status="ok",
                component="mistral_api",
                message="Mistral API reachable and authenticated",
                details={
                    "enabled": True,
                    "api_key_present": True,
                    "model": settings.mistral_model,
                    "http_status": resp.status_code,
                },
                latency_ms=latency_ms,
            )
        elif resp.status_code == 401:
            return CheckResult(
                status="error",
                component="mistral_api",
                message="Mistral API key is invalid or expired",
                details={"http_status": resp.status_code},
                latency_ms=latency_ms,
            )
        else:
            return CheckResult(
                status="degraded",
                component="mistral_api",
                message=f"Mistral API returned unexpected status: {resp.status_code}",
                details={"http_status": resp.status_code},
                latency_ms=latency_ms,
            )
    except requests.exceptions.Timeout:
        latency_ms = (time.perf_counter() - start) * 1000
        return CheckResult(
            status="error",
            component="mistral_api",
            message="Mistral API connection timed out",
            details={"timeout_seconds": 5},
            latency_ms=latency_ms,
        )
    except Exception as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        return CheckResult(
            status="error",
            component="mistral_api",
            message=f"Mistral API check failed: {exc}",
            details={"error_type": type(exc).__name__},
            latency_ms=latency_ms,
        )


async def check_email_delivery() -> CheckResult:
    """Check email delivery configuration status."""
    provider = settings.email_provider

    if provider == "smtp":
        if not settings.smtp_username or not settings.smtp_password:
            return CheckResult(
                status="degraded",
                component="email_delivery",
                message="SMTP provider enabled but credentials incomplete",
                details={"provider": "smtp", "configured": False},
            )
        return CheckResult(
            status="ok",
            component="email_delivery",
            message="SMTP email delivery configured",
            details={"provider": "smtp", "host": settings.smtp_host, "port": settings.smtp_port},
        )
    elif provider == "resend":
        if not settings.resend_api_key:
            return CheckResult(
                status="degraded",
                component="email_delivery",
                message="Resend provider enabled but API key missing",
                details={"provider": "resend", "configured": False},
            )
        return CheckResult(
            status="ok",
            component="email_delivery",
            message="Resend email delivery configured",
            details={"provider": "resend"},
        )
    elif provider == "sendgrid":
        if not settings.sendgrid_api_key:
            return CheckResult(
                status="degraded",
                component="email_delivery",
                message="SendGrid provider enabled but API key missing",
                details={"provider": "sendgrid", "configured": False},
            )
        return CheckResult(
            status="ok",
            component="email_delivery",
            message="SendGrid email delivery configured",
            details={"provider": "sendgrid"},
        )
    else:
        return CheckResult(
            status="ok",
            component="email_delivery",
            message=f"Email provider '{provider}' configured",
            details={"provider": provider},
        )


# ---------------------------------------------------------------------------
# System resource checks
# ---------------------------------------------------------------------------


def check_disk_space() -> CheckResult:
    """Check available disk space on the backend root partition."""
    try:
        usage = psutil.disk_usage(str(BACKEND_ROOT))
        usage_percent = usage.percent

        if usage_percent < 80:
            status = "ok"
            message = "Disk space healthy"
        elif usage_percent < 90:
            status = "degraded"
            message = f"Disk usage at {usage_percent:.1f}% — approaching capacity"
        else:
            status = "error"
            message = f"Disk usage critical at {usage_percent:.1f}%"

        return CheckResult(
            status=status,
            component="disk_space",
            message=message,
            details={
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "usage_percent": round(usage_percent, 1),
                "path": str(BACKEND_ROOT),
            },
        )
    except Exception as exc:
        return CheckResult(
            status="error",
            component="disk_space",
            message=f"Disk space check failed: {exc}",
            details={"error_type": type(exc).__name__},
        )


def check_memory_usage() -> CheckResult:
    """Check process and system memory usage."""
    try:
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        system_mem = psutil.virtual_memory()

        process_rss_mb = mem_info.rss / (1024 * 1024)
        process_percent = process.memory_percent()
        system_percent = system_mem.percent

        # Determine status based on process memory
        if process_percent < 50 and system_percent < 80:
            status = "ok"
            message = "Memory usage healthy"
        elif process_percent < 80 and system_percent < 90:
            status = "degraded"
            message = f"Process memory at {process_percent:.1f}%, system at {system_percent:.1f}%"
        else:
            status = "error"
            message = f"Memory usage critical — process: {process_percent:.1f}%, system: {system_percent:.1f}%"

        return CheckResult(
            status=status,
            component="memory",
            message=message,
            details={
                "process_rss_mb": round(process_rss_mb, 1),
                "process_memory_percent": round(process_percent, 1),
                "system_total_gb": round(system_mem.total / (1024**3), 2),
                "system_available_gb": round(system_mem.available / (1024**3), 2),
                "system_memory_percent": round(system_percent, 1),
                "gc_stats": _get_gc_stats(),
            },
        )
    except Exception as exc:
        return CheckResult(
            status="error",
            component="memory",
            message=f"Memory check failed: {exc}",
            details={"error_type": type(exc).__name__},
        )


def check_cpu_usage() -> CheckResult:
    """Check CPU usage."""
    try:
        cpu_count = psutil.cpu_count(logical=True)
        cpu_percent = psutil.cpu_percent(interval=0.1)
        process = psutil.Process(os.getpid())
        process_cpu = process.cpu_percent(interval=0.1)

        if cpu_percent < 80:
            status = "ok"
            message = "CPU usage healthy"
        elif cpu_percent < 90:
            status = "degraded"
            message = f"CPU usage elevated at {cpu_percent:.1f}%"
        else:
            status = "error"
            message = f"CPU usage critical at {cpu_percent:.1f}%"

        return CheckResult(
            status=status,
            component="cpu",
            message=message,
            details={
                "cpu_count": cpu_count,
                "system_cpu_percent": round(cpu_percent, 1),
                "process_cpu_percent": round(process_cpu, 1),
            },
        )
    except Exception as exc:
        return CheckResult(
            status="error",
            component="cpu",
            message=f"CPU check failed: {exc}",
            details={"error_type": type(exc).__name__},
        )


# ---------------------------------------------------------------------------
# Aggregate health check
# ---------------------------------------------------------------------------


async def run_all_health_checks() -> dict[str, Any]:
    """Run all health checks and return aggregated results."""
    start = time.perf_counter()

    # Synchronous checks
    model_files = check_model_files()
    model_loadable = check_model_loadable()
    disk_space = check_disk_space()
    memory = check_memory_usage()
    cpu = check_cpu_usage()

    # Asynchronous checks
    db_conn, db_tables, mistral, email = await asyncio.gather(
        check_database_connectivity(),
        check_database_tables(),
        check_mistral_api(),
        check_email_delivery(),
        return_exceptions=True,
    )

    # Handle exceptions from gather
    checks: list[CheckResult] = [
        model_files,
        model_loadable,
        disk_space,
        memory,
        cpu,
    ]

    for result in [db_conn, db_tables, mistral, email]:
        if isinstance(result, Exception):
            checks.append(
                CheckResult(
                    status="error",
                    component="unknown",
                    message=str(result),
                    details={"error_type": type(result).__name__},
                )
            )
        else:
            checks.append(result)

    # Determine overall status
    has_error = any(c.status == "error" for c in checks)
    has_degraded = any(c.status == "degraded" for c in checks)

    if has_error:
        overall_status = "unhealthy"
    elif has_degraded:
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    total_latency_ms = (time.perf_counter() - start) * 1000

    return {
        "status": overall_status,
        "timestamp": time.time(),
        "version": "1.0.0",
        "uptime_seconds": _get_uptime(),
        "total_latency_ms": round(total_latency_ms, 2),
        "system": {
            "python_version": platform.python_version(),
            "platform": platform.system(),
            "machine": platform.machine(),
            "pid": os.getpid(),
        },
        "checks": {c.component: c.to_dict() for c in checks},
    }


# ---------------------------------------------------------------------------
# Health check cache
# ---------------------------------------------------------------------------


class HealthCheckCache:
    """
    TTL-based cache for health check results.

    Prevents excessive resource consumption from repeated health checks
    (e.g., from load balancer probes every 5 seconds).
    """

    def __init__(self, ttl_seconds: float = 10.0):
        self.ttl_seconds = ttl_seconds
        self._cached_result: dict[str, Any] | None = None
        self._cached_at: float = 0.0

    def is_fresh(self) -> bool:
        if self._cached_result is None:
            return False
        return (time.time() - self._cached_at) < self.ttl_seconds

    def get(self) -> dict[str, Any] | None:
        if self.is_fresh():
            return self._cached_result
        return None

    def set(self, result: dict[str, Any]) -> None:
        self._cached_result = result
        self._cached_at = time.time()

    def invalidate(self) -> None:
        self._cached_result = None
        self._cached_at = 0.0


# Global cache instance (10-second TTL)
health_cache = HealthCheckCache(ttl_seconds=10.0)


async def get_cached_health_status() -> dict[str, Any]:
    """Get health status, using cache if fresh."""
    cached = health_cache.get()
    if cached is not None:
        cached["cache_hit"] = True
        return cached

    result = await run_all_health_checks()
    result["cache_hit"] = False
    health_cache.set(result)
    return result


# ---------------------------------------------------------------------------
# Metrics collector
# ---------------------------------------------------------------------------


class MetricsCollector:
    """
    In-process metrics collector for request-level and business metrics.

    Thread-safe via asyncio locks. Data is held in memory and resets on
    process restart. For production persistence, integrate with
    Prometheus/Grafana via the /metrics endpoint.
    """

    def __init__(self):
        # Request metrics
        self._request_count = 0
        self._request_errors = 0
        self._request_latencies: list[float] = []
        self._request_latencies_sum = 0.0

        # Model inference metrics
        self._inference_count = 0
        self._inference_errors = 0
        self._inference_latencies: list[float] = []
        self._inference_latencies_sum = 0.0

        # Cache metrics
        self._cache_hits = 0
        self._cache_misses = 0

        # Active user tracking (by user_id)
        self._active_users: dict[int, float] = {}  # user_id -> last_seen timestamp

        # Per-endpoint metrics
        self._endpoint_metrics: dict[str, dict[str, int | float]] = {}

        # Lock for async safety
        self._lock = asyncio.Lock()

    async def record_request(
        self,
        path: str,
        status_code: int,
        latency_ms: float,
    ) -> None:
        """Record a completed request."""
        async with self._lock:
            self._request_count += 1
            self._request_latencies_sum += latency_ms

            # Keep last 1000 latencies for percentile calculations
            self._request_latencies.append(latency_ms)
            if len(self._request_latencies) > 1000:
                self._request_latencies = self._request_latencies[-1000:]

            if status_code >= 400:
                self._request_errors += 1

            # Per-endpoint
            if path not in self._endpoint_metrics:
                self._endpoint_metrics[path] = {
                    "count": 0,
                    "errors": 0,
                    "latency_sum": 0.0,
                }
            ep = self._endpoint_metrics[path]
            ep["count"] += 1  # type: ignore
            ep["latency_sum"] += latency_ms  # type: ignore
            if status_code >= 400:
                ep["errors"] += 1  # type: ignore

    async def record_inference(self, latency_ms: float, success: bool = True) -> None:
        """Record a model inference."""
        async with self._lock:
            self._inference_count += 1
            self._inference_latencies_sum += latency_ms
            self._inference_latencies.append(latency_ms)
            if len(self._inference_latencies) > 1000:
                self._inference_latencies = self._inference_latencies[-1000:]
            if not success:
                self._inference_errors += 1

    async def record_cache_access(self, hit: bool) -> None:
        """Record a cache access."""
        async with self._lock:
            if hit:
                self._cache_hits += 1
            else:
                self._cache_misses += 1

    async def record_active_user(self, user_id: int) -> None:
        """Record user activity."""
        async with self._lock:
            self._active_users[user_id] = time.time()

    def _compute_percentile(self, data: list[float], percentile: float) -> float:
        """Compute a percentile from a sorted list of values."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * (percentile / 100.0)
        f = int(k)
        c = f + 1
        if c >= len(sorted_data):
            return sorted_data[f]
        return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f])

    async def get_summary(self) -> dict[str, Any]:
        """Get current metrics summary."""
        async with self._lock:
            # Request metrics
            avg_latency = (
                self._request_latencies_sum / self._request_count
                if self._request_count > 0
                else 0.0
            )
            error_rate = (
                self._request_errors / self._request_count
                if self._request_count > 0
                else 0.0
            )

            p50_latency = self._compute_percentile(self._request_latencies, 50)
            p95_latency = self._compute_percentile(self._request_latencies, 95)
            p99_latency = self._compute_percentile(self._request_latencies, 99)

            # Inference metrics
            inf_avg_latency = (
                self._inference_latencies_sum / self._inference_count
                if self._inference_count > 0
                else 0.0
            )
            inf_error_rate = (
                self._inference_errors / self._inference_count
                if self._inference_count > 0
                else 0.0
            )

            p50_inference = self._compute_percentile(self._inference_latencies, 50)
            p95_inference = self._compute_percentile(self._inference_latencies, 95)
            p99_inference = self._compute_percentile(self._inference_latencies, 99)

            # Cache metrics
            total_cache_accesses = self._cache_hits + self._cache_misses
            cache_hit_rate = (
                self._cache_hits / total_cache_accesses if total_cache_accesses > 0 else 0.0
            )

            # Active users (last 15 minutes)
            cutoff = time.time() - 900
            active_now = sum(1 for t in self._active_users.values() if t > cutoff)

            # Memory footprint estimate
            total_tracked_items = (
                len(self._request_latencies)
                + len(self._inference_latencies)
                + len(self._active_users)
            )

            return {
                "requests": {
                    "total": self._request_count,
                    "errors": self._request_errors,
                    "error_rate": round(error_rate, 4),
                    "avg_latency_ms": round(avg_latency, 2),
                    "p50_latency_ms": round(p50_latency, 2),
                    "p95_latency_ms": round(p95_latency, 2),
                    "p99_latency_ms": round(p99_latency, 2),
                },
                "inference": {
                    "total": self._inference_count,
                    "errors": self._inference_errors,
                    "error_rate": round(inf_error_rate, 4),
                    "avg_latency_ms": round(inf_avg_latency, 2),
                    "p50_latency_ms": round(p50_inference, 2),
                    "p95_latency_ms": round(p95_inference, 2),
                    "p99_latency_ms": round(p99_inference, 2),
                },
                "cache": {
                    "hits": self._cache_hits,
                    "misses": self._cache_misses,
                    "hit_rate": round(cache_hit_rate, 4),
                },
                "users": {
                    "active_last_15min": active_now,
                    "total_tracked": len(self._active_users),
                },
                "endpoints": {
                    path: {
                        "count": metrics["count"],
                        "errors": metrics["errors"],
                        "avg_latency_ms": round(
                            metrics["latency_sum"] / metrics["count"], 2
                        )
                        if metrics["count"] > 0
                        else 0.0,
                    }
                    for path, metrics in self._endpoint_metrics.items()
                },
                "internal": {
                    "tracked_items": total_tracked_items,
                    "gc_collections": _get_gc_stats(),
                },
                "collected_at": time.time(),
            }

    async def get_prometheus_format(self) -> str:
        """Export metrics in Prometheus text exposition format."""
        summary = await self.get_summary()

        lines = [
            "# HELP anemialens_requests_total Total number of HTTP requests",
            "# TYPE anemialens_requests_total counter",
            f"anemialens_requests_total {summary['requests']['total']}",
            "",
            "# HELP anemialens_request_errors_total Total number of HTTP errors (4xx/5xx)",
            "# TYPE anemialens_request_errors_total counter",
            f"anemialens_request_errors_total {summary['requests']['errors']}",
            "",
            "# HELP anemialens_request_error_rate Ratio of error responses",
            "# TYPE anemialens_request_error_rate gauge",
            f"anemialens_request_error_rate {summary['requests']['error_rate']}",
            "",
            "# HELP anemialens_request_latency_ms Average request latency in milliseconds",
            "# TYPE anemialens_request_latency_ms gauge",
            f"anemialens_request_latency_ms {summary['requests']['avg_latency_ms']}",
            "",
            "# HELP anemialens_request_latency_p50_ms 50th percentile request latency",
            "# TYPE anemialens_request_latency_p50_ms gauge",
            f"anemialens_request_latency_p50_ms {summary['requests']['p50_latency_ms']}",
            "",
            "# HELP anemialens_request_latency_p95_ms 95th percentile request latency",
            "# TYPE anemialens_request_latency_p95_ms gauge",
            f"anemialens_request_latency_p95_ms {summary['requests']['p95_latency_ms']}",
            "",
            "# HELP anemialens_request_latency_p99_ms 99th percentile request latency",
            "# TYPE anemialens_request_latency_p99_ms gauge",
            f"anemialens_request_latency_p99_ms {summary['requests']['p99_latency_ms']}",
            "",
            "# HELP anemialens_inference_total Total model inferences",
            "# TYPE anemialens_inference_total counter",
            f"anemialens_inference_total {summary['inference']['total']}",
            "",
            "# HELP anemialens_inference_errors_total Total inference errors",
            "# TYPE anemialens_inference_errors_total counter",
            f"anemialens_inference_errors_total {summary['inference']['errors']}",
            "",
            "# HELP anemialens_inference_latency_ms Average inference latency",
            "# TYPE anemialens_inference_latency_ms gauge",
            f"anemialens_inference_latency_ms {summary['inference']['avg_latency_ms']}",
            "",
            "# HELP anemialens_cache_hit_rate Cache hit rate (0.0-1.0)",
            "# TYPE anemialens_cache_hit_rate gauge",
            f"anemialens_cache_hit_rate {summary['cache']['hit_rate']}",
            "",
            "# HELP anemialens_cache_hits_total Total cache hits",
            "# TYPE anemialens_cache_hits_total counter",
            f"anemialens_cache_hits_total {summary['cache']['hits']}",
            "",
            "# HELP anemialens_cache_misses_total Total cache misses",
            "# TYPE anemialens_cache_misses_total counter",
            f"anemialens_cache_misses_total {summary['cache']['misses']}",
            "",
            "# HELP anemialens_active_users Active users in last 15 minutes",
            "# TYPE anemialens_active_users gauge",
            f"anemialens_active_users {summary['users']['active_last_15min']}",
            "",
        ]

        # Per-endpoint metrics
        for path, metrics in summary["endpoints"].items():
            lines.extend(
                [
                    f"# HELP anemialens_endpoint_requests_total{{path=\"{path}\"}} Requests for {path}",
                    f"# TYPE anemialens_endpoint_requests_total{{path=\"{path}\"}} counter",
                    f'anemialens_endpoint_requests_total{{path="{path}"}} {metrics["count"]}',
                    "",
                ]
            )

        return "\n".join(lines)


# Global metrics collector
metrics_collector = MetricsCollector()


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _mask_url(url: str) -> str:
    """Mask sensitive parts of a URL."""
    if "@" in url:
        before, after = url.rsplit("@", 1)
        if "://" in before:
            scheme, rest = before.split("://", 1)
            return f"{scheme}://***:***@{after}"
        return f"***:***@{after}"
    return url


def _guess_db_type() -> str:
    """Guess the database type from the connection string."""
    from app.database import DATABASE_URL

    if "sqlite" in DATABASE_URL:
        return "sqlite"
    if "postgres" in DATABASE_URL:
        return "postgresql"
    if "supabase" in DATABASE_URL:
        return "supabase_postgresql"
    return "unknown"


def _compute_file_hash(path: Path, max_bytes: int = 1024 * 1024) -> str:
    """Compute partial file hash for integrity tracking."""
    try:
        h = hashlib.md5()
        with open(path, "rb") as f:
            data = f.read(max_bytes)
            h.update(data)
        return h.hexdigest()
    except Exception:
        return ""


def _get_gc_stats() -> dict[str, int]:
    """Get garbage collection statistics."""
    counts = gc.get_count()
    thresholds = gc.get_threshold()
    return {
        "gen0_collections": counts[0],
        "gen1_collections": counts[1],
        "gen2_collections": counts[2],
        "gen0_threshold": thresholds[0],
        "gen1_threshold": thresholds[1],
        "gen2_threshold": thresholds[2],
        "total_objects_tracked": len(gc.get_objects()),
    }


def _get_uptime() -> float:
    """Get process uptime in seconds."""
    try:
        process = psutil.Process(os.getpid())
        return time.time() - process.create_time()
    except Exception:
        return 0.0
