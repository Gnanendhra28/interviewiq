from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from apps.api.app.core.config import settings
from apps.api.app.core.exceptions import DomainException
from apps.api.app.core.logging import logger
from apps.api.app.core.middleware import (
    RequestCorrelationMiddleware,
    SecurityHeadersMiddleware,
    get_current_request_id,
)
from apps.api.app.modules.candidates.presentation.router import (
    cand_invitation_router,
    candidate_router,
)
from apps.api.app.modules.identity.presentation.router import router as identity_router
from apps.api.app.modules.integrations.presentation.router import router as integrations_router
from apps.api.app.modules.interview_intelligence.presentation.router import (
    interview_intelligence_router,
)
from apps.api.app.modules.interviews.presentation.router import interviews_router
from apps.api.app.modules.job_roles.presentation.router import job_roles_router
from apps.api.app.modules.knowledge_rag.presentation.router import knowledge_rag_router
from apps.api.app.modules.notifications.presentation.router import router as notifications_router
from apps.api.app.modules.organizations.presentation.router import (
    invitation_router as org_invitation_router,
)
from apps.api.app.modules.organizations.presentation.router import org_router
from apps.api.app.modules.reports.presentation.pdf_router import router as pdf_router
from apps.api.app.modules.reports.presentation.recruiter_router import (
    decision_router,
    recruiter_router,
)
from apps.api.app.modules.reports.presentation.router import reports_router
from apps.api.app.modules.resumes.presentation.router import resume_router
from apps.api.app.modules.shared.presentation.health_router import health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail-fast production configuration validation
    settings.validate_production_configuration()
    logger.info(f"Started InterviewIQ API in environment '{settings.ENVIRONMENT}'")
    yield
    logger.info("Shutting down InterviewIQ API gracefully.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)

# Operational & Security Middlewares
app.add_middleware(RequestCorrelationMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# CORS Configuration (ADR 013: allow_credentials=True for HttpOnly cookies)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DomainException)
async def domain_exception_handler(request: Request, exc: DomainException):
    req_id = get_current_request_id()
    status_code = status.HTTP_400_BAD_REQUEST
    if exc.code in ("AUTH_INVALID_CREDENTIALS", "AUTH_INVALID_TOKEN", "AUTH_REQUIRED"):
        status_code = status.HTTP_401_UNAUTHORIZED
    elif exc.code in ("AUTH_ACCOUNT_SUSPENDED", "AUTH_PERMISSION_DENIED", "AUTH_ORGANIZATION_ACCESS_DENIED", "AUTH_CANDIDATE_ACCESS_DENIED", "PRIVILEGE_ESCALATION_DENIED"):
        status_code = status.HTTP_403_FORBIDDEN
    elif exc.code in ("AUTH_USER_NOT_FOUND", "AUTH_ORGANIZATION_NOT_FOUND", "CANDIDATE_NOT_FOUND", "MEMBERSHIP_NOT_FOUND", "SKILL_NOT_FOUND", "ROLE_NOT_FOUND", "INVITATION_NOT_FOUND", "RESUME_NOT_FOUND", "KNOWLEDGE_BASE_NOT_FOUND", "KNOWLEDGE_DOCUMENT_NOT_FOUND", "INTERVIEW_SESSION_NOT_FOUND", "INTERVIEW_REPORT_NOT_FOUND", "HIRING_DECISION_NOT_FOUND"):
        status_code = status.HTTP_404_NOT_FOUND
    elif exc.code in ("DUPLICATE_RESUME_UPLOAD", "DUPLICATE_JOB_ROLE_CODE"):
        status_code = status.HTTP_409_CONFLICT
    elif exc.code == "FILE_TOO_LARGE":
        status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    elif exc.code in ("INVALID_FILE_EXTENSION", "INVALID_FILE_SIGNATURE", "FILE_FORMAT_MISMATCH"):
        status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    elif exc.code == "RATE_LIMIT_EXCEEDED":
        status_code = status.HTTP_429_TOO_MANY_REQUESTS

    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "request_id": req_id
            }
        },
        headers={"X-Request-ID": req_id} if req_id else None
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    req_id = get_current_request_id()
    logger.error(f"[UNHANDLED EXCEPTION] [{req_id}] {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred. Please contact support.",
                "request_id": req_id
            }
        },
        headers={"X-Request-ID": req_id} if req_id else None
    )


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "environment": settings.ENVIRONMENT}


# Mount API V1 Routers & Health Router
app.include_router(health_router)
app.include_router(identity_router, prefix=settings.API_V1_STR)
app.include_router(org_router, prefix=settings.API_V1_STR)
app.include_router(org_invitation_router, prefix=settings.API_V1_STR)
app.include_router(candidate_router, prefix=settings.API_V1_STR)
app.include_router(cand_invitation_router, prefix=settings.API_V1_STR)
app.include_router(resume_router, prefix=settings.API_V1_STR)
app.include_router(job_roles_router, prefix=settings.API_V1_STR)
app.include_router(knowledge_rag_router, prefix=settings.API_V1_STR)
app.include_router(interviews_router, prefix=settings.API_V1_STR)
app.include_router(interview_intelligence_router, prefix=settings.API_V1_STR)
app.include_router(reports_router, prefix=settings.API_V1_STR)
app.include_router(recruiter_router, prefix=settings.API_V1_STR)
app.include_router(decision_router, prefix=settings.API_V1_STR)
app.include_router(integrations_router, prefix=settings.API_V1_STR)
app.include_router(notifications_router, prefix=settings.API_V1_STR)
app.include_router(pdf_router, prefix=settings.API_V1_STR)
