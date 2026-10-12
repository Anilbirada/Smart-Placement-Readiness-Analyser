# System Design — Smart Placement Readiness Analyser

## 1. Architectural Pattern
The system follows a **modular monolith** architecture with strict separation of concerns between presentation, HTTP routing, business orchestration, pure domain engines, and relational persistence.

```
[ React + TypeScript Frontend (frontend/src/) ]
                      |
             REST / JSON (HTTP/1.1)
                      v
[ FastAPI Router & Security Middleware (backend/app/api/routes.py) ]
                      |
                      v
[ Service Orchestration Layer (backend/app/services/placement_service.py) ]
        /                                   \
       v                                     v
[ Assessment Engine ]               [ Recommendation Engine ]
(backend/app/assessments/engine.py) (backend/app/recommendations/engine.py)
       \                                     /
        v                                   v
[ SQLAlchemy Relational Persistence (backend/app/models/entities.py) ]
                      |
                      v
[ SQLite Local DB / PostgreSQL Production DB ]
```

## 2. Core Modules
- **`backend/app/core/config.py`:** Centralised configuration for scoring model versions (`1.0.0`), question bank versions (`1.0.0`), readiness category thresholds, CORS origins, and optional AI settings.
- **`backend/app/core/security.py`:** PBKDF2-HMAC-SHA256 password hashing, HMAC-SHA256 signed session tokens, XSS HTML/script stripping, and PII/secret log redaction.
- **`backend/app/assessments/engine.py`:** Pure Python grading and role-readiness calculation functions with zero UI coupling.
- **`backend/app/recommendations/engine.py`:** Rule-based gap prioritisation, completed-activity deduplication, and schema-validated optional AI study-tip enrichment.
- **`backend/app/services/placement_service.py`:** Transaction management, attempt lifecycle control, recommendation synchronisation, and progress aggregation.
- **`frontend/src/App.tsx` & `frontend/src/services/api.ts`:** Typed React UI implementing all 8 required student workflows with explicit empty states and error banners.
