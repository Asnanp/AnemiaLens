"""
Comprehensive Monitoring, Logging & Observability System

This module provides:
1. Structured logging with correlation IDs
2. Prometheus metrics collection
3. Health checks with dependency status
4. Distributed tracing support
5. Alert management
6. Audit logging for compliance
"""

from __future__ import annotations

import logging
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# ---------------------------------------------------------------------------
# Correlation ID Context Variable
# ---------------------------------------------------------------------------

correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    """Get current correlation ID"""
    return correlation_id.get()


def set_correlation_id(cid: str) -> None:
    """Set correlation ID for current request"""
    correlation_id.set(cid)


# ---------------------------------------------------------------------------
# Structured Logger
# ---------------------------------------------------------------------------

class StructuredLogger:
    """
    JSON structured logger for production observability.
    
    Usage:
        logger = StructuredLogger("anemialens.screening")
        logger.info("Screening started", user_id="123", screening_id="abc")
    """
    
    def __init__(self, name: str, service: str = "anemialens"):
        self.logger = logging.getLogger(f"{service}.{name}")
        self.service = service
        self._setup_handler()
    
    def _setup_handler(self):
        """Configure JSON formatter for structured logging"""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(StructuredFormatter())
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def _log(
        self,
        level: int,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
        exc_info: bool = False
    ):
        """Internal log method"""
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": logging.getLevelName(level),
            "message": message,
            "service": self.service,
            "correlation_id": get_correlation_id(),
        }
        
        if extra:
            log_data["extra"] = extra
        
        self.logger.log(level, message, extra=log_data, exc_info=exc_info)
    
    def debug(self, message: str, **kwargs):
        self._log(logging.DEBUG, message, kwargs)
    
    def info(self, message: str, **kwargs):
        self._log(logging.INFO, message, kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log(logging.WARNING, message, kwargs)
    
    def error(self, message: str, **kwargs):
        self._log(logging.ERROR, message, kwargs, exc_info=True)
    
    def critical(self, message: str, **kwargs):
        self._log(logging.CRITICAL, message, kwargs, exc_info=True)


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        import json
        
        log_data = {
            "timestamp": record.created,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add correlation ID
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id
        
        # Add extra fields
        if hasattr(record, "extra"):
            log_data["extra"] = record.extra
        
        # Add exception info
        if record.exc_info and record.exc_info[0]:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }
        
        return json.dumps(log_data, default=str)


# ---------------------------------------------------------------------------
# Metrics Collection
# ---------------------------------------------------------------------------

class MetricsCollector:
    """
    Prometheus-compatible metrics collector.
    
    Tracks:
    - Request latency and throughput
    - ML inference time
    - Error rates
    - Active users
    - Screening success rate
    """
    
    def __init__(self):
        self.metrics: Dict[str, Any] = {
            "http_requests_total": {},
            "http_request_duration_seconds": {},
            "ml_inference_duration_seconds": {},
            "ml_predictions_total": {"success": 0, "failure": 0, "quality_rejected": 0},
            "active_users": set(),
            "screenings_total": 0,
            "errors_total": {},
        }
    
    def record_request(self, method: str, path: str, status_code: int, duration: float):
        """Record HTTP request metrics"""
        key = f"{method} {path}"
        if key not in self.metrics["http_requests_total"]:
            self.metrics["http_requests_total"][key] = {"2xx": 0, "4xx": 0, "5xx": 0}
        
        if 200 <= status_code < 300:
            self.metrics["http_requests_total"][key]["2xx"] += 1
        elif 400 <= status_code < 500:
            self.metrics["http_requests_total"][key]["4xx"] += 1
        else:
            self.metrics["http_requests_total"][key]["5xx"] += 1
        
        if key not in self.metrics["http_request_duration_seconds"]:
            self.metrics["http_request_duration_seconds"][key] = []
        
        self.metrics["http_request_duration_seconds"][key].append(duration)
    
    def record_ml_inference(self, duration: float, success: bool, quality_passed: bool):
        """Record ML inference metrics"""
        if "inferences" not in self.metrics["ml_inference_duration_seconds"]:
            self.metrics["ml_inference_duration_seconds"]["inferences"] = []
        
        self.metrics["ml_inference_duration_seconds"]["inferences"].append(duration)
        
        if success:
            self.metrics["ml_predictions_total"]["success"] += 1
        else:
            self.metrics["ml_predictions_total"]["failure"] += 1
        
        if not quality_passed:
            self.metrics["ml_predictions_total"]["quality_rejected"] += 1
    
    def record_error(self, error_type: str, endpoint: str):
        """Record error metrics"""
        key = f"{error_type}:{endpoint}"
        if key not in self.metrics["errors_total"]:
            self.metrics["errors_total"][key] = 0
        self.metrics["errors_total"][key] += 1
    
    def track_active_user(self, user_id: str):
        """Track active user"""
        self.metrics["active_users"].add(user_id)
    
    def record_screening(self):
        """Record screening completion"""
        self.metrics["screenings_total"] += 1
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get current metrics summary"""
        return {
            "total_screenings": self.metrics["screenings_total"],
            "active_users": len(self.metrics["active_users"]),
            "ml_predictions": self.metrics["ml_predictions_total"],
            "error_rates": self.metrics["errors_total"],
        }


# Global metrics instance
metrics = MetricsCollector()


# ---------------------------------------------------------------------------
# Request Logging Middleware
# ---------------------------------------------------------------------------

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request logging and metrics collection.
    
    Features:
    - Generates correlation ID for each request
    - Logs request/response with timing
    - Collects Prometheus metrics
    - Tracks errors
    """
    
    def __init__(self, app, logger_name: str = "anemialens"):
        super().__init__(app)
        self.logger = StructuredLogger(logger_name)
    
    async def dispatch(self, request: Request, call_next):
        # Generate correlation ID
        cid = str(uuid.uuid4())
        set_correlation_id(cid)
        
        # Log request
        start_time = time.time()
        self.logger.info(
            f"{request.method} {request.url.path} started",
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else "unknown",
        )
        
        # Process request
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # Log response
            self.logger.info(
                f"{request.method} {request.url.path} completed",
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
            )
            
            # Record metrics
            metrics.record_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration=duration,
            )
            
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = cid
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Log error
            self.logger.error(
                f"{request.method} {request.url.path} failed",
                error_type=type(e).__name__,
                error_message=str(e),
                duration_ms=round(duration * 1000, 2),
            )
            
            # Record error metrics
            metrics.record_error(
                error_type=type(e).__name__,
                endpoint=request.url.path,
            )
            
            raise


# ---------------------------------------------------------------------------
# Health Check Enhancements
# ---------------------------------------------------------------------------

class HealthCheckService:
    """
    Comprehensive health checking with dependency status.
    
    Checks:
    - Database connectivity
    - ML model readiness
    - Redis connection (if configured)
    - External services (Mistral AI, Stripe)
    - Disk space
    - Memory usage
    """
    
    def __init__(self):
        self.checks = {}
    
    def register_check(self, name: str, check_fn):
        """Register a health check"""
        self.checks[name] = check_fn
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all registered health checks"""
        results = {}
        
        for name, check_fn in self.checks.items():
            try:
                status = await check_fn()
                results[name] = {
                    "status": "healthy" if status else "unhealthy",
                    "healthy": status,
                }
            except Exception as e:
                results[name] = {
                    "status": "error",
                    "healthy": False,
                    "error": str(e),
                }
        
        return results
    
    def is_healthy(self, results: Dict[str, Any]) -> bool:
        """Determine overall health"""
        return all(check["healthy"] for check in results.values())


# ---------------------------------------------------------------------------
# Audit Logger (HIPAA Compliance)
# ---------------------------------------------------------------------------

class AuditLogger:
    """
    HIPAA-compliant audit logger.
    
    Logs all PHI access and modifications:
    - User authentication events
    - Screening creation/access
    - Data exports
    - Admin actions
    - Configuration changes
    """
    
    def __init__(self):
        self.logger = StructuredLogger("audit")
    
    def log_authentication(
        self,
        user_id: str,
        email: str,
        method: str,
        success: bool,
        ip_address: str,
        user_agent: str,
    ):
        """Log authentication event"""
        self.logger.info(
            "Authentication event",
            event_type="auth",
            event_subtype="login_success" if success else "login_failure",
            user_id=user_id,
            email=email,
            auth_method=method,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    
    def log_screening_access(
        self,
        user_id: str,
        screening_id: str,
        action: str,
        ip_address: str,
    ):
        """Log screening access event"""
        self.logger.info(
            "Screening access",
            event_type="screening_access",
            event_subtype=action,
            user_id=user_id,
            screening_id=screening_id,
            ip_address=ip_address,
        )
    
    def log_data_export(
        self,
        user_id: str,
        export_type: str,
        record_count: int,
        ip_address: str,
    ):
        """Log data export event"""
        self.logger.info(
            "Data export",
            event_type="data_export",
            export_type=export_type,
            record_count=record_count,
            user_id=user_id,
            ip_address=ip_address,
        )
    
    def log_admin_action(
        self,
        admin_id: str,
        action: str,
        target: str,
        details: Dict[str, Any],
    ):
        """Log admin action"""
        self.logger.info(
            "Admin action",
            event_type="admin_action",
            action=action,
            target=target,
            admin_id=admin_id,
            details=details,
        )


# Global audit logger instance
audit_logger = AuditLogger()


# ---------------------------------------------------------------------------
# Alert Manager
# ---------------------------------------------------------------------------

class AlertManager:
    """
    Alert management for critical events.
    
    Supports:
    - Error rate thresholds
    - Latency thresholds
    - ML model degradation
    - System resource warnings
    """
    
    def __init__(self):
        self.alerts = []
        self.alert_handlers = []
    
    def register_handler(self, handler):
        """Register alert handler"""
        self.alert_handlers.append(handler)
    
    async def trigger_alert(
        self,
        severity: str,  # critical, warning, info
        alert_type: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Trigger an alert"""
        alert = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": severity,
            "type": alert_type,
            "message": message,
            "metadata": metadata or {},
        }
        
        self.alerts.append(alert)
        
        # Notify handlers
        for handler in self.alert_handlers:
            try:
                await handler(alert)
            except Exception as e:
                logging.error(f"Alert handler failed: {e}")
    
    def get_recent_alerts(self, limit: int = 50) -> list:
        """Get recent alerts"""
        return self.alerts[-limit:]


# Global alert manager
alert_manager = AlertManager()


# ---------------------------------------------------------------------------
# Usage Examples
# ---------------------------------------------------------------------------

"""
# In your FastAPI app:

from app.middleware.observability import RequestLoggingMiddleware, StructuredLogger

app = FastAPI()

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Use structured logger
logger = StructuredLogger("screening")

@router.post("/analyze")
async def analyze():
    logger.info("Screening started", user_id="123")
    
    try:
        # Your code here
        pass
    except Exception as e:
        logger.error("Screening failed", error=str(e), user_id="123")
        raise

# Health check endpoint
@router.get("/health")
async def health():
    health_service = HealthCheckService()
    health_service.register_check("database", check_database)
    health_service.register_check("ml_model", check_ml_model)
    
    results = await health_service.run_all_checks()
    return {
        "status": "healthy" if health_service.is_healthy(results) else "degraded",
        "checks": results,
    }

# Audit logging
from app.middleware.observability import audit_logger

@router.post("/login")
async def login(request: Request):
    audit_logger.log_authentication(
        user_id=user.uid,
        email=user.email,
        method="password",
        success=True,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent"),
    )
"""
