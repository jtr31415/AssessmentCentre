from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.db import SessionLocal
from app.routers import admin, auth, booking, public, slots
from app.routers.booking import admin_router as booking_admin_router
from app.routers.booking import me_router as booking_me_router
from app.seed import seed_admin_and_config


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        seed_admin_and_config(db)
    finally:
        db.close()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Candidate Assessment Platform", lifespan=lifespan)
    app.add_middleware(
        SessionMiddleware,
        secret_key=get_settings().session_secret,
        https_only=False,
        same_site="lax",
    )
    app.include_router(public.router)
    app.include_router(auth.router)
    app.include_router(admin.router)
    app.include_router(slots.router)
    app.include_router(booking.router)
    app.include_router(booking_admin_router)
    app.include_router(booking_me_router)
    return app


app = create_app()
