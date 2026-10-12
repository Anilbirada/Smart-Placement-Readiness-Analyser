from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict

from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.routes import router as placement_router
from backend.app.core.config import (
    ALLOWED_ORIGINS,
    APP_NAME,
    APP_VERSION,
    BACKEND_HOST,
    BACKEND_PORT,
    ENABLE_HISTORY,
)
from backend.app.core.database import AnalysisRecord, SessionLocal, init_db
from backend.app.repositories.seed_data import seed_reference_data
from backend.app.schemas.analysis import (
    AnalysisResponse,
    AnalyzeRequest,
    FeatureSummary,
    ModelStatusResponse,
    RiskCategory,
)
from backend.app.services.model_service import analyze_with_available_model, get_model_status


def bootstrap_database() -> None:
    init_db()
    db = SessionLocal()
    try:
        seed_reference_data(db)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    bootstrap_database()
    yield


bootstrap_database()

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=(
        "Transparent placement preparation and skill-gap analysis service with rule-based scoring, "
        "configurable role-skill mappings, personalized learning plans, and progress tracking."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+)(:\d+)?",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Student-ID"],
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


from fastapi.exceptions import RequestValidationError


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    if request.url.path == "/api/v1/analyze" and exc.errors():
        first_msg = exc.errors()[0].get("msg", "Invalid request.")
        return JSONResponse(status_code=422, content={"detail": first_msg})
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please try again."},
    )


app.include_router(placement_router)


# Preserved legacy URL detector endpoints so existing tests in test_api.py continue to pass
@app.get("/api/v1/model/status", response_model=ModelStatusResponse, tags=["Legacy Compatibility"])
def model_status() -> ModelStatusResponse:
    status_info = get_model_status()
    return ModelStatusResponse(
        model_loaded=status_info.model_loaded,
        model_version=status_info.model_version,
        feature_schema_version=status_info.feature_schema_version,
        fallback_mode_active=status_info.fallback_mode_active,
        available_evaluation_metadata=status_info.available_evaluation_metadata,
        is_compatible=status_info.is_compatible,
    )


@app.post("/api/v1/analyze", response_model=AnalysisResponse, tags=["Legacy Compatibility"])
def analyze(payload: AnalyzeRequest) -> AnalysisResponse:
    try:
        result = analyze_with_available_model(payload.url)
        features = FeatureSummary(**result["features"])
        response = AnalysisResponse(
            analysis_id=str(uuid.uuid4()),
            submitted_url=result["submitted_url"],
            risk_category=RiskCategory(result["risk_category"]),
            analysis_method=result["analysis_method"],
            model_version=result.get("model_version"),
            score=result.get("score"),
            features=features,
            indicators=result["indicators"],
            recommendations=result["recommendations"],
            timestamp=result["timestamp"],
            limitations=result["limitations"],
            confidence_note=result["confidence_note"],
            model_status=result.get("model_status", "fallback-mode-active"),
        )
        if ENABLE_HISTORY:
            session = SessionLocal()
            try:
                record = AnalysisRecord(
                    analysis_id=response.analysis_id,
                    submitted_url=response.submitted_url,
                    risk_category=response.risk_category.value,
                    analysis_method=response.analysis_method,
                    model_version=response.model_version,
                    score=str(response.score) if response.score is not None else None,
                    status="completed",
                )
                session.add(record)
                session.commit()
            finally:
                session.close()
        return response
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@app.get("/api/v1/history", tags=["Legacy Compatibility"])
def list_history(limit: int = Query(default=20, ge=1, le=100)) -> Dict[str, Any]:
    if not ENABLE_HISTORY:
        return {"records": [], "enabled": False}
    session = SessionLocal()
    try:
        rows = session.query(AnalysisRecord).order_by(AnalysisRecord.created_at.desc()).limit(limit).all()
        data = [
            {
                "analysis_id": row.analysis_id,
                "submitted_url": row.submitted_url,
                "risk_category": row.risk_category,
                "analysis_method": row.analysis_method,
                "model_version": row.model_version,
                "score": row.score,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ]
        return {"records": data, "enabled": True}
    finally:
        session.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app.main:app", host=BACKEND_HOST, port=BACKEND_PORT, reload=False)
