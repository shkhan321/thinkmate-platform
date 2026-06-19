from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api import admin, auth, consent, dialogue, sessions, tasks, worksheet
from app.config import Settings, get_settings
from app.database import Base, make_engine, make_session_factory
from app.seed import seed_database


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or get_settings()
    app = FastAPI(title="ThinkMate Pilot API", version="0.1.0")
    app.state.settings = active_settings
    app.state.engine = make_engine(active_settings.database_url)
    app.state.SessionLocal = make_session_factory(app.state.engine)

    Base.metadata.create_all(app.state.engine)
    with app.state.SessionLocal() as db:
        seed_database(db)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(consent.router)
    app.include_router(tasks.router)
    app.include_router(sessions.router)
    app.include_router(dialogue.router)
    app.include_router(worksheet.router)
    app.include_router(admin.router)

    @app.get("/health")
    def health():
        database_status = "ok"
        try:
            with app.state.SessionLocal() as db:
                db.execute(text("select 1"))
        except Exception:
            database_status = "error"
        return {
            "status": "ok" if database_status == "ok" else "degraded",
            "app_env": active_settings.app_env,
            "database": database_status,
            "model_mode": "huggingface" if active_settings.hf_api_token else "demo",
            "hf_model": active_settings.hf_model,
            "consent_version": active_settings.consent_version,
        }

    return app


app = create_app()
