from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from apps.api.app.core.config import settings
from apps.api.app.core.exceptions import InterviewIQException
from apps.api.app.core.logging import logger, setup_logging
from apps.api.app.modules.audit_logging.api.router import (
    router as audit_logging_router,
)
from apps.api.app.modules.background_jobs.api.router import (
    router as background_jobs_router,
)
from apps.api.app.modules.candidates.api.router import (
    router as candidates_router,
)
from apps.api.app.modules.identity.api.router import router as identity_router
from apps.api.app.modules.interview_intelligence.api.router import (
    router as interview_intelligence_router,
)
from apps.api.app.modules.interviews.api.router import (
    router as interviews_router,
)
from apps.api.app.modules.job_roles.api.router import (
    router as job_roles_router,
)
from apps.api.app.modules.knowledge_rag.api.router import (
    router as knowledge_rag_router,
)
from apps.api.app.modules.organizations.api.router import (
    router as organizations_router,
)
from apps.api.app.modules.reports.api.router import router as reports_router
from apps.api.app.modules.resumes.api.router import router as resumes_router
from apps.api.app.modules.shared.api.router import router as shared_router

setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(InterviewIQException)
async def interviewiq_exception_handler(
    request: Request, exc: InterviewIQException
):
    logger.error(
        f"InterviewIQException [{exc.code}]: {exc.message} - Details: {exc.details}"
    )
    status_code = 400
    if exc.code == "UNAUTHORIZED":
        status_code = 401
    elif exc.code == "FORBIDDEN":
        status_code = 403
    elif exc.code == "NOT_FOUND":
        status_code = 404
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "ok",
        "environment": settings.ENVIRONMENT,
        "version": "0.1.0",
    }


@app.get("/ready", tags=["System"])
async def readiness_check():
    return {
        "status": "ready",
        "services": {
            "database": "connected",
            "redis": "connected",
            "ai_provider": settings.AI_PROVIDER,
            "embedding_provider": settings.EMBEDDING_PROVIDER,
            "embedding_dimension": settings.EMBEDDING_DIMENSION,
        },
    }


# Register all 12 Bounded Context Routers under API v1 prefix
v1_prefix = settings.API_V1_STR
app.include_router(
    identity_router, prefix=f"{v1_prefix}/identity", tags=["1. Identity & Access"]
)
app.include_router(
    organizations_router,
    prefix=f"{v1_prefix}/organizations",
    tags=["2. Organizations & Membership"],
)
app.include_router(
    candidates_router, prefix=f"{v1_prefix}/candidates", tags=["3. Candidates"]
)
app.include_router(
    resumes_router, prefix=f"{v1_prefix}/resumes", tags=["4. Resumes"]
)
app.include_router(
    job_roles_router, prefix=f"{v1_prefix}/job-roles", tags=["5. Job Roles"]
)
app.include_router(
    knowledge_rag_router,
    prefix=f"{v1_prefix}/knowledge-rag",
    tags=["6. Knowledge & RAG Retrieval"],
)
app.include_router(
    interviews_router,
    prefix=f"{v1_prefix}/interviews",
    tags=["7. Interview Orchestration"],
)
app.include_router(
    interview_intelligence_router,
    prefix=f"{v1_prefix}/intelligence",
    tags=["8. Interview Intelligence"],
)
app.include_router(
    reports_router, prefix=f"{v1_prefix}/reports", tags=["9. Reports"]
)
app.include_router(
    background_jobs_router, prefix=f"{v1_prefix}/jobs", tags=["10. Background Jobs"]
)
app.include_router(
    audit_logging_router, prefix=f"{v1_prefix}/audit", tags=["11. Audit Logging"]
)
app.include_router(
    shared_router, prefix=f"{v1_prefix}/shared", tags=["12. Shared Infrastructure"]
)
