from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text

from app.api import admin, auth, consent, dialogue, project, sessions, tasks, worksheet
from app.config import Settings, get_settings
from app.database import Base, make_engine, make_session_factory
from app.seed import parse_pilot_access_codes, seed_database
from app.services.model_adapter import active_model_mode, active_model_name


DEFAULT_ADMIN_PASSWORDS = {"", "change-me", "change-this-before-deploying"}


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or get_settings()
    validate_settings(active_settings)
    app = FastAPI(title="ThinkMate Pilot API", version="0.1.0")
    app.state.settings = active_settings
    app.state.engine = make_engine(active_settings.database_url)
    app.state.SessionLocal = make_session_factory(app.state.engine)

    Base.metadata.create_all(app.state.engine)
    ensure_schema_migrations(app.state.engine)
    with app.state.SessionLocal() as db:
        seed_database(
            db,
            pilot_students=parse_pilot_access_codes(active_settings.pilot_access_codes),
            include_demo_students=active_settings.seed_demo_students,
        )

    origins = parse_cors_origins(active_settings.cors_origins)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=origins != ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(consent.router)
    app.include_router(project.router)
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
            "model_mode": active_model_mode(active_settings),
            "model_name": active_model_name(active_settings),
            "hf_model": active_settings.hf_model,
            "consent_version": active_settings.consent_version,
        }

    mount_frontend(app)

    return app


def ensure_schema_migrations(engine) -> None:
    """Lightweight, idempotent column adds so existing databases pick up new
    columns without a full migration tool. Safe on SQLite and PostgreSQL."""
    table_columns = {
        "students": {
            "display_name": "VARCHAR(120)",
            "project_title": "VARCHAR(200)",
            "project_goal": "TEXT",
        },
        "sessions": {
            "final_answer": "TEXT",
        },
    }
    inspector = inspect(engine)
    with engine.begin() as connection:
        for table, columns in table_columns.items():
            if not inspector.has_table(table):
                continue
            existing = {column["name"] for column in inspector.get_columns(table)}
            for name, ddl in columns.items():
                if name not in existing:
                    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


def validate_settings(settings: Settings) -> None:
    if settings.app_env.lower() == "production" and settings.admin_password in DEFAULT_ADMIN_PASSWORDS:
        raise RuntimeError("ADMIN_PASSWORD must be changed before production startup.")


def parse_cors_origins(raw_origins: str) -> list[str]:
    if raw_origins.strip() == "*":
        return ["*"]
    origins = [origin.strip() for origin in raw_origins.replace("\n", ",").split(",")]
    return [origin for origin in origins if origin]


def mount_frontend(app: FastAPI) -> None:
    dist_dir = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    index_file = dist_dir / "index.html"
    assets_dir = dist_dir / "assets"
    if not index_file.exists():
        return

    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API route not found")

        dist_root = dist_dir.resolve()
        requested = (dist_dir / full_path).resolve()
        if requested.is_file() and requested.is_relative_to(dist_root):
            return FileResponse(requested)
        return FileResponse(index_file)


app = create_app()
