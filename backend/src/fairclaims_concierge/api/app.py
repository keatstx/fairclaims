"""Application factory.

Wires settings, structlog, FAQ store (with bundled seed), LLM backend,
concierge route, and health probe. Phase 4 adds the questions log
store + admin router; Phase 5 adds the static-site mount.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from fairclaims_concierge.api.dependencies import init_dependencies
from fairclaims_concierge.api.routes import admin, concierge, health
from fairclaims_concierge.config import Settings
from fairclaims_concierge.core.faq_import import seed_default_faqs_if_empty
from fairclaims_concierge.core.faq_store import FAQStore
from fairclaims_concierge.core.questions_log_store import QuestionsLogStore
from fairclaims_concierge.llm.factory import create_language_model


def _configure_structlog(settings: Settings) -> None:
    renderer: structlog.types.Processor
    if settings.log_renderer == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(0),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def create_app() -> FastAPI:
    settings = Settings()
    _configure_structlog(settings)
    logger = structlog.get_logger()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        db_path = Path(settings.db_path).expanduser()
        db_path.parent.mkdir(parents=True, exist_ok=True)

        faq_store = FAQStore(str(db_path))
        await faq_store.initialize()
        seeded = await seed_default_faqs_if_empty(faq_store)
        total = len(await faq_store.list_all())
        logger.info(
            "faq_store_ready",
            db_path=str(db_path),
            seeded=seeded,
            total=total,
        )

        llm = create_language_model(settings)

        questions_log_store = QuestionsLogStore(str(db_path))
        await questions_log_store.initialize()

        init_dependencies(
            settings=settings,
            faq_store=faq_store,
            llm=llm,
            questions_log_store=questions_log_store,
        )

        logger.info(
            "fairclaims_concierge_started",
            llm_backend=settings.llm_backend,
            concierge_enabled=settings.concierge_enabled,
            admin_enabled=bool(settings.admin_token),
        )

        try:
            yield
        finally:
            await faq_store.close()
            await questions_log_store.close()
            logger.info("fairclaims_concierge_stopped")

    app = FastAPI(
        title="FairClaims Concierge",
        version="0.1.0",
        lifespan=lifespan,
    )

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
        )

    app.include_router(health.router)
    app.include_router(concierge.router)
    app.include_router(admin.router)

    # Static site mount LAST so API routes win precedence. `html=True`
    # makes StaticFiles serve `index.html` for `/` and any path that
    # resolves to a directory containing index.html.
    static_root = Path(settings.static_dir).expanduser()
    if static_root.exists():
        app.mount(
            "/",
            StaticFiles(directory=str(static_root), html=True),
            name="static",
        )
        logger.info("static_site_mounted", static_dir=str(static_root))
    else:
        logger.warning(
            "static_dir_missing_skipping_mount",
            static_dir=str(static_root),
        )

    return app
