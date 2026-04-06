# Architecture: Clean Architecture + Modular Monolith (Hybrid for Medical AI)

## Overview
AnemiaLens employs a **hybrid architecture** combining Clean Architecture principles with a Modular Monolith structure. This approach was chosen because medical AI applications require strict separation of concerns (domain logic must be pure and testable) while benefiting from unified deployment and strong module boundaries.

The architecture ensures that the ML inference pipeline, clinical decision-making, and user management are isolated modules with explicit public APIs, while maintaining a single deployment unit for operational simplicity. This enables future extraction of modules (e.g., ML service) into microservices if scale demands it.

## Decision Rationale
- **Project type:** Medical AI screening platform with complex ML pipeline and clinical workflows
- **Tech stack:** FastAPI (Python) + React/TypeScript, PostgreSQL/Supabase
- **Key factor:** Regulatory compliance requirements (HIPAA), need for auditability, and future multi-tenant SaaS expansion
- **Team size:** Currently small, but designed for 5-15 person team
- **Scale requirements:** 100K+ concurrent users, 99.9% uptime, global deployment

## Folder Structure

### Backend (Python/FastAPI)
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                         # Composition root, lifespan, middleware
│   ├── config.py                       # Pydantic settings
│   ├── database.py                     # DB engine/session (infrastructure)
│   ├── dependencies.py                 # DI providers
│   ├── health_checks.py                # Health/readiness probes
│   │
│   ├── domain/                         # DOMAIN LAYER (pure business logic)
│   │   ├── entities/
│   │   │   ├── user.py                 # User entity with invariants
│   │   │   ├── screening.py            # Screening entity
│   │   │   └── audit_log.py            # Audit trail entity
│   │   ├── value_objects/
│   │   │   ├── hemoglobin.py           # Hb value with validation
│   │   │   ├── risk_score.py           # Risk score with bounds
│   │   │   └── image_quality.py        # Quality metrics VO
│   │   ├── repositories/               # Interfaces only (no implementations)
│   │   │   ├── user_repository.py
│   │   │   ├── screening_repository.py
│   │   │   └── audit_repository.py
│   │   ├── services/                   # Domain services (business rules)
│   │   │   ├── triage_service.py
│   │   │   ├── risk_calculation_service.py
│   │   │   └── clinical_decision_service.py
│   │   └── exceptions/
│   │       ├── domain_errors.py
│   │       └── validation_errors.py
│   │
│   ├── application/                    # APPLICATION LAYER (use cases)
│   │   ├── use_cases/
│   │   │   ├── screening/
│   │   │   │   ├── perform_screening.py
│   │   │   │   ├── get_screening.py
│   │   │   │   ├── list_screenings.py
│   │   │   │   └── delete_screening.py
│   │   │   ├── auth/
│   │   │   │   ├── register_user.py
│   │   │   │   ├── authenticate_user.py
│   │   │   │   └── refresh_token.py
│   │   │   └── reporting/
│   │   │       ├── export_csv.py
│   │   │       └── generate_clinical_brief.py
│   │   ├── services/                   # Application services
│   │   │   ├── image_quality_service.py
│   │   │   ├── guidance_service.py
│   │   │   ├── email_service.py
│   │   │   └── analytics_service.py
│   │   ├── dto/                        # Data Transfer Objects
│   │   │   ├── screening_dto.py
│   │   │   ├── auth_dto.py
│   │   │   └── report_dto.py
│   │   └── interfaces/                 # Ports for external systems
│   │       ├── ml_inference_port.py
│   │       ├── email_port.py
│   │       └── storage_port.py
│   │
│   ├── infrastructure/                 # INFRASTRUCTURE LAYER (adapters)
│   │   ├── ml/                         # ML inference implementations
│   │   │   ├── models/                 # ML model artifacts
│   │   │   ├── inference/
│   │   │   │   ├── archive_fusion_inference.py
│   │   │   │   ├── efficientnet_inference.py
│   │   │   │   ├── ensemble_inference.py
│   │   │   │   └── runtime_calibration.py
│   │   │   ├── features/
│   │   │   │   ├── image_preprocessing.py
│   │   │   │   ├── feature_extraction.py
│   │   │   │   └── quality_assessment.py
│   │   │   └── pipeline.py             # ML pipeline orchestrator
│   │   ├── database/                   # DB implementations
│   │   │   ├── repositories/
│   │   │   │   ├── sqlalchemy_user_repo.py
│   │   │   │   ├── sqlalchemy_screening_repo.py
│   │   │   │   └── sqlalchemy_audit_repo.py
│   │   │   ├── models/                 # ORM models
│   │   │   │   ├── user_orm.py
│   │   │   │   ├── screening_orm.py
│   │   │   │   └── audit_log_orm.py
│   │   │   └── migrations/             # Alembic migrations
│   │   │       └── versions/
│   │   ├── external/                   # External service adapters
│   │   │   ├── mistral_ai_adapter.py
│   │   │   ├── stripe_adapter.py
│   │   │   ├── gmail_adapter.py
│   │   │   └── google_oauth_adapter.py
│   │   ├── cache/
│   │   │   ├── redis_cache.py
│   │   │   └── inference_cache.py
│   │   └── storage/
│   │       └── image_storage.py
│   │
│   ├── presentation/                   # PRESENTATION LAYER (API)
│   │   ├── api/
│   │   │   ├── v1/                     # API versioning
│   │   │   │   ├── auth.py
│   │   │   │   ├── screening.py
│   │   │   │   ├── history.py
│   │   │   │   ├── billing.py
│   │   │   │   ├── admin.py
│   │   │   │   └── email_report.py
│   │   │   └── websocket.py            # Real-time features
│   │   ├── middleware/
│   │   │   ├── rate_limit.py
│   │   │   ├── security_headers.py
│   │   │   ├── request_logging.py
│   │   │   ├── memory_guard.py
│   │   │   └── metrics.py
│   │   ├── schemas.py                  # Pydantic request/response schemas
│   │   └── dependencies.py             # FastAPI dependencies
│   │
│   └── shared/                         # SHARED KERNEL
│       ├── utils/
│       │   ├── security.py             # JWT, password hashing
│       │   ├── validators.py
│       │   └── formatters.py
│       ├── constants.py
│       └── types.py
│
├── tests/
│   ├── unit/                           # Unit tests
│   │   ├── domain/
│   │   ├── application/
│   │   └── infrastructure/
│   ├── integration/                    # Integration tests
│   │   ├── api/
│   │   └── database/
│   └── e2e/                            # End-to-end tests
│       └── screening_flow.py
│
├── scripts/                            # Training/evaluation scripts
├── requirements.txt
├── .env.example
└── Dockerfile
```

### Frontend (React/TypeScript)
```
frontend/
├── src/
│   ├── main.tsx                        # Entry point
│   ├── App.tsx                         # App shell
│   ├── api.ts                          # API client
│   ├── types.ts                        # TypeScript types
│   │
│   ├── features/                       # Feature modules
│   │   ├── screening/
│   │   │   ├── components/
│   │   │   │   ├── CaptureStep.tsx
│   │   │   │   ├── QualityStep.tsx
│   │   │   │   ├── IntakeStep.tsx
│   │   │   │   └── ResultStep.tsx
│   │   │   ├── hooks/
│   │   │   │   ├── useScreening.ts
│   │   │   │   └── useImageUpload.ts
│   │   │   ├── api.ts                  # Screening API calls
│   │   │   └── types.ts
│   │   ├── auth/
│   │   │   ├── components/
│   │   │   │   ├── LoginForm.tsx
│   │   │   │   ├── RegisterForm.tsx
│   │   │   │   └── GoogleSignIn.tsx
│   │   │   ├── hooks/
│   │   │   │   └── useAuth.ts
│   │   │   └── api.ts
│   │   ├── history/
│   │   │   ├── components/
│   │   │   │   ├── HistoryList.tsx
│   │   │   │   ├── HistoryCard.tsx
│   │   │   │   └── ExportModal.tsx
│   │   │   └── hooks/
│   │   │       └── useHistory.ts
│   │   └── billing/
│   │       ├── components/
│   │       │   ├── PricingTable.tsx
│   │       │   └── CheckoutModal.tsx
│   │       └── api.ts
│   │
│   ├── components/                     # Shared UI components
│   │   ├── ui/                         # Primitives
│   │   │   ├── Button.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Dialog.tsx
│   │   │   ├── Input.tsx
│   │   │   └── ...
│   │   └── layout/
│   │       ├── Navbar.tsx
│   │       ├── Footer.tsx
│   │       └── Sidebar.tsx
│   │
│   ├── hooks/                          # Shared hooks
│   ├── utils/                          # Utilities
│   ├── styles/                         # Global styles
│   ├── i18n/                           # Internationalization
│   └── pages/                          # Route pages
│       ├── LandingPage.tsx
│       ├── DashboardPage.tsx
│       └── AdminPage.tsx
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/                            # Playwright tests
│
├── package.json
├── vite.config.ts
└── tsconfig.json
```

## Dependency Rules

### Backend (Clean Architecture)
- ✅ **Domain** → nothing (pure business logic, no external dependencies)
- ✅ **Application** → Domain only (use cases depend on entities and repository interfaces)
- ✅ **Infrastructure** → Application + Domain (implements repository interfaces and ports)
- ✅ **Presentation** → Application (calls use cases, never touches infrastructure directly)
- ❌ Domain must NOT import from Application, Infrastructure, or Presentation
- ❌ Application must NOT import from Infrastructure or Presentation
- ❌ Presentation must NOT import from Infrastructure directly

### Frontend (Feature-Sliced Design)
- ✅ Features are isolated and communicate via public APIs (hooks, components)
- ✅ Shared components (ui/, layout/) have no feature dependencies
- ✅ Feature hooks encapsulate API calls and state management
- ❌ Features must NOT import from other features' internals
- ❌ Shared components must NOT import feature-specific code

## Layer/Module Communication

### Backend Communication Patterns
1. **API → Use Cases**: Controllers call use case classes with DTOs
2. **Use Cases → Domain Services**: Use cases orchestrate domain services
3. **Domain Services → Repositories**: Domain services use repository interfaces
4. **Infrastructure → Implements**: Infrastructure layer implements repository interfaces and ports
5. **Dependency Injection**: FastAPI's `Depends()` for wiring components

### Frontend Communication Patterns
1. **Components → Hooks**: Components consume feature hooks
2. **Hooks → API**: Hooks make API calls and manage state
3. **Features → Features**: Features communicate via props or global state
4. **State Management**: React Context for auth, React Query for server state

## Key Principles

### 1. Domain Purity
All business logic lives in the domain layer with zero external dependencies. Entities enforce their own invariants:
```python
# Domain entity enforces its own rules
class Screening:
    def __init__(self, hemoglobin: HemoglobinValue, quality: ImageQualityScore):
        if not quality.passes_threshold():
            raise ScreeningQualityError("Image quality insufficient")
        self.hemoglobin = hemoglobin
        self.quality = quality
```

### 2. Dependency Inversion
Infrastructure implements interfaces defined in domain/application:
```python
# Domain defines interface
class ScreeningRepository(Protocol):
    async def save(self, screening: Screening) -> str: ...
    async def get(self, uid: str) -> Screening: ...

# Infrastructure implements it
class SQLAlchemyScreeningRepository:
    async def save(self, screening: Screening) -> str:
        # SQLAlchemy implementation
```

### 3. Use Case Isolation
Each use case is a single class with one responsibility:
```python
@dataclass
class PerformScreening:
    ml_inference: MLInferencePort
    triage_service: TriageService
    repo: ScreeningRepository

    async def execute(self, command: ScreeningCommand) -> ScreeningResult:
        # Single responsibility: orchestrate screening flow
```

### 4. Module Boundaries
Features expose only their public API via `__init__.py`:
```typescript
// features/screening/index.ts
export { ScreeningWizard } from './components/ScreeningWizard';
export { useScreening } from './hooks/useScreening';
export type { ScreeningResult } from './types';
// No internal components exported
```

### 5. Explicit Error Handling
Errors are domain-specific and handled at appropriate layers:
```python
try:
    result = await use_case.execute(command)
except DomainValidationError as e:
    raise HTTPException(status_code=400, detail=str(e))
except ScreeningQualityError as e:
    return QualityFailedResponse(reason=e.reason)
```

## Code Examples

### Example 1: Complete Screening Flow (Clean Architecture)

**Domain Layer** (Pure business logic):
```python
# app/domain/entities/screening.py
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

@dataclass
class Screening:
    uid: str
    user_id: str | None
    image_url: str
    hemoglobin_estimate: float
    risk_score: float
    triage_result: str
    created_at: datetime
    quality_passed: bool

    @classmethod
    def create(cls, user_id: str | None, image_url: str) -> 'Screening':
        return cls(
            uid=str(uuid4()),
            user_id=user_id,
            image_url=image_url,
            hemoglobin_estimate=0.0,
            risk_score=0.0,
            triage_result="pending",
            created_at=datetime.utcnow(),
            quality_passed=False
        )

    def update_result(self, hemoglobin: float, risk: float, triage: str):
        if hemoglobin < 0 or hemoglobin > 20:
            raise ValueError(f"Invalid hemoglobin: {hemoglobin}")
        self.hemoglobin_estimate = hemoglobin
        self.risk_score = risk
        self.triage_result = triage
```

**Application Layer** (Use case orchestration):
```python
# app/application/use_cases/screening/perform_screening.py
from dataclasses import dataclass
from ...interfaces.ml_inference_port import MLInferencePort
from ...domain.services.triage_service import TriageService
from ...domain.repositories.screening_repository import ScreeningRepository
from ...domain.entities.screening import Screening

@dataclass
class PerformScreeningUseCase:
    ml_inference: MLInferencePort
    triage_service: TriageService
    repository: ScreeningRepository

    async def execute(self, image_path: str, symptoms: list[str]) -> dict:
        # 1. Run ML inference
        prediction = await self.ml_inference.predict(image_path)
        
        # 2. Check quality
        if not prediction.quality_passed:
            return {"status": "quality_failed", "reason": prediction.quality_reason}
        
        # 3. Create screening entity
        screening = Screening.create(user_id=None, image_url=image_path)
        screening.update_result(
            hemoglobin=prediction.hemoglobin,
            risk=prediction.risk_score,
            triage=self.triage_service.assess(prediction, symptoms)
        )
        
        # 4. Persist
        uid = await self.repository.save(screening)
        
        return {
            "status": "complete",
            "uid": uid,
            "hemoglobin": screening.hemoglobin_estimate,
            "risk": screening.risk_score,
            "triage": screening.triage_result
        }
```

**Infrastructure Layer** (ML implementation):
```python
# app/infrastructure/ml/inference/archive_fusion_inference.py
from ....application.interfaces.ml_inference_port import MLInferencePort
from dataclasses import dataclass

@dataclass
class PredictionResult:
    hemoglobin: float
    risk_score: float
    quality_passed: bool
    quality_reason: str | None

class ArchiveFusionInference(MLInferencePort):
    def __init__(self, model_path: str):
        self.model = self._load_model(model_path)
    
    async def predict(self, image_path: str) -> PredictionResult:
        # ML implementation details
        features = self._extract_features(image_path)
        prediction = self.model.predict(features)
        
        return PredictionResult(
            hemoglobin=prediction['hemoglobin'],
            risk_score=prediction['risk'],
            quality_passed=prediction['quality'] > 0.8,
            quality_reason=None
        )
```

**Presentation Layer** (API endpoint):
```python
# app/presentation/api/v1/screening.py
from fastapi import APIRouter, Depends, UploadFile, File
from ....application.use_cases.screening.perform_screening import PerformScreeningUseCase
from ....infrastructure.ml.inference.archive_fusion_inference import ArchiveFusionInference
from ....infrastructure.database.repositories.sqlalchemy_screening_repo import SQLAlchemyScreeningRepository

router = APIRouter(prefix="/api/v1/screening", tags=["screening"])

@router.post("/analyze")
async def analyze_screening(
    image: UploadFile = File(...),
    symptoms: list[str] = [],
    use_case: PerformScreeningUseCase = Depends()
):
    # Save image temporarily
    image_path = await save_upload(image)
    
    # Execute use case
    result = await use_case.execute(image_path, symptoms)
    
    return result
```

### Example 2: Dependency Injection Setup
```python
# app/dependencies.py
from fastapi import Depends
from .application.use_cases.screening.perform_screening import PerformScreeningUseCase
from .infrastructure.ml.inference.archive_fusion_inference import ArchiveFusionInference
from .infrastructure.database.repositories.sqlalchemy_screening_repo import SQLAlchemyScreeningRepository
from .domain.services.triage_service import TriageService

async def get_ml_inference() -> ArchiveFusionInference:
    return ArchiveFusionInference(model_path="models/archive-fusion-v7.joblib")

async def get_screening_repo() -> SQLAlchemyScreeningRepository:
    return SQLAlchemyScreeningRepository()

async def get_triage_service() -> TriageService:
    return TriageService()

async def get_perform_screening_use_case(
    ml_inference = Depends(get_ml_inference),
    repo = Depends(get_screening_repo),
    triage = Depends(get_triage_service)
) -> PerformScreeningUseCase:
    return PerformScreeningUseCase(ml_inference, triage, repo)
```

### Example 3: Frontend Feature Module
```typescript
// features/screening/hooks/useScreening.ts
import { useState, useCallback } from 'react';
import { screeningApi } from '../api';
import type { ScreeningResult, ScreeningStep } from '../types';

export function useScreening() {
  const [step, setStep] = useState<ScreeningStep>('capture');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ScreeningResult | null>(null);

  const analyze = useCallback(async (image: File, symptoms: string[]) => {
    setLoading(true);
    setStep('analyzing');
    
    try {
      const response = await screeningApi.analyze(image, symptoms);
      setResult(response);
      setStep('result');
    } catch (error) {
      if (error.status === 400 && error.code === 'QUALITY_FAILED') {
        setStep('quality_failed');
      } else {
        setStep('error');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  return { step, loading, result, analyze, reset: () => setStep('capture') };
}
```

## Anti-Patterns

### ❌ Never Skip Layers
```python
# BAD: API directly accessing ORM model
@router.post("/analyze")
async def analyze(db: Session = Depends(get_db)):
    screening = ScreeningORM()  # Direct ORM access in presentation
    screening.result = ml_model.predict(image)  # ML in presentation layer
    db.add(screening)
```

### ❌ Never Import Infrastructure in Domain
```python
# BAD: Domain importing SQLAlchemy
from app.infrastructure.database import Base  # VIOLATION!
from sqlalchemy import Column, Integer

class Screening(Base):  # Domain entity coupled to SQLAlchemy
```

### ❌ Never Put Business Logic in Use Cases
```python
# BAD: Business logic in use case instead of domain
class PerformScreeningUseCase:
    async def execute(self, image_path: str):
        if prediction.hemoglobin < 7:  # Business rule in use case!
            risk = "severe"
        elif prediction.hemoglobin < 10:  # Should be in domain service
            risk = "moderate"
```

### ❌ Never Couple Features to Each Other
```typescript
// BAD: Feature reaching into another feature's internals
import { InternalHelper } from '../../auth/components/InternalHelper';  // VIOLATION!
import { authStore } from '../../auth/stores/authStore';  // VIOLATION!
```

### ❌ Never Mix Concerns in Components
```typescript
// BAD: Component doing API calls, state management, and business logic
function ResultView() {
  const [data, setData] = useState();
  
  useEffect(() => {
    // API call inside component
    fetch('/api/analyze')
      .then(res => res.json())
      .then(data => {
        // Business logic in component
        if (data.hemoglobin < 7) {
          data.severity = 'severe';
        }
        setData(data);
      });
  }, []);
  
  // Should use hook that encapsulates all this
}
```

## Migration Strategy

### Phase 1: Foundation (Week 1-2)
- Create domain layer structure
- Extract entities and value objects
- Define repository interfaces

### Phase 2: Application Layer (Week 2-3)
- Create use case classes
- Move business logic to domain services
- Implement dependency injection

### Phase 3: Infrastructure (Week 3-4)
- Move ML inference to infrastructure
- Implement repository interfaces
- Create external service adapters

### Phase 4: Presentation (Week 4-5)
- Refactor API endpoints to use use cases
- Add API versioning (v1 prefix)
- Implement proper error handling

### Phase 5: Frontend (Week 5-6)
- Reorganize into feature-sliced design
- Create shared component library
- Implement proper state management

## Testing Strategy

### Unit Tests
- Domain entities: Test invariants and business rules
- Use cases: Test orchestration logic with mocked dependencies
- Infrastructure: Test implementations against contracts

### Integration Tests
- API endpoints: Test full request/response cycle
- Repository implementations: Test against real database
- ML pipeline: Test end-to-end inference

### E2E Tests
- Screening flow: Complete user journey from upload to result
- Auth flow: Registration, login, token refresh
- Error scenarios: Quality failures, network errors
