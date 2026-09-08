"""
AegisAI Governance OS - Main Application Entrypoint.
FastAPI Application serving all 17 authoritative frameworks, unified controls,
crosswalk mappings, AI inventory, intake, threat modeling, and evidence management.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from aegis_app.core.config import settings, validate_production_settings
from aegis_app.core.database import engine, Base
from aegis_app.models import models, regulatory  # noqa: F401  (register all tables on Base.metadata)
from aegis_app.api import (
    auth, ai_systems, frameworks, controls, crosswalk,
    assessments, evidence, risks, security, copilot,
    dashboard, reports, audit,
    model_registry, agent_registry, vendor_registry, org_structure, graph,
    regulatory as regulatory_api,
    onboarding, sme,
)
from aegis_app.seed.demo_data import seed_demo_data

logger = logging.getLogger("aegis_app")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail closed: refuse to boot with development defaults in production.
    validate_production_settings()

    # Startup: Create tables if not exist.
    # NOTE: production deployments should use Alembic migrations (backend/alembic/)
    # instead of relying on create_all; this call is a no-op against a schema that
    # migrations already manage (create_all only adds missing tables, never alters
    # existing ones), so it is safe to leave in place as a local-dev convenience.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Demo data is a development/sales-demo convenience only. It is never seeded
    # in production (validate_production_settings() above already refuses to boot
    # if SEED_DEMO_DATA is true and ENVIRONMENT=production, but we double-gate here
    # in case this lifespan is ever reused from a different entrypoint).
    if settings.SEED_DEMO_DATA and settings.ENVIRONMENT != "production":
        await seed_demo_data()
    else:
        logger.info("Demo data seeding skipped (SEED_DEMO_DATA=%s, ENVIRONMENT=%s)",
                     settings.SEED_DEMO_DATA, settings.ENVIRONMENT)
    yield
    # Shutdown
    await engine.dispose()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Enterprise AI Trust, Risk & Compliance Operating System. "
        "Unified Governance across EU AI Act, NIST AI RMF, NIST AI 600-1, "
        "EU CRA, OWASP GenAI/Agentic, GDPR, DORA, NIS2, and 17 authoritative standards."
    ),
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request, call_next):
    """Baseline security response headers (OWASP secure headers)."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    response.headers.setdefault("Permissions-Policy", "geolocation=(), camera=(), microphone=()")
    # API serves JSON only; a strict CSP is safe here and blocks any injected markup.
    # The interactive docs pages (/docs, /redoc) legitimately load a CDN bundle.
    if not request.url.path.rstrip("/").endswith(("/docs", "/redoc")):
        response.headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
    if settings.ENVIRONMENT == "production":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response

# Register API v1 Routers
api_v1_prefix = settings.API_V1_STR
app.include_router(auth.router, prefix=api_v1_prefix)
app.include_router(ai_systems.router, prefix=api_v1_prefix)
app.include_router(frameworks.router, prefix=api_v1_prefix)
app.include_router(controls.router, prefix=api_v1_prefix)
app.include_router(crosswalk.router, prefix=api_v1_prefix)
app.include_router(assessments.router, prefix=api_v1_prefix)
app.include_router(evidence.router, prefix=api_v1_prefix)
app.include_router(risks.router, prefix=api_v1_prefix)
app.include_router(security.router, prefix=api_v1_prefix)
app.include_router(copilot.router, prefix=api_v1_prefix)
app.include_router(dashboard.router, prefix=api_v1_prefix)
app.include_router(reports.router, prefix=api_v1_prefix)
app.include_router(audit.router, prefix=api_v1_prefix)
app.include_router(model_registry.router, prefix=api_v1_prefix)
app.include_router(agent_registry.router, prefix=api_v1_prefix)
app.include_router(vendor_registry.router, prefix=api_v1_prefix)
app.include_router(org_structure.router, prefix=api_v1_prefix)
app.include_router(graph.router, prefix=api_v1_prefix)
app.include_router(regulatory_api.router, prefix=api_v1_prefix)
app.include_router(onboarding.router, prefix=api_v1_prefix)
app.include_router(sme.router, prefix=api_v1_prefix)

@app.get("/")
async def root():
    return {
        "platform": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "operational",
        "supported_frameworks_count": 17,
        "documentation": f"{settings.API_V1_STR}/docs",
        "legal_disclaimer": settings.LEGAL_DISCLAIMER
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "database": "connected"}
