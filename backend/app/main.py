from fastapi import FastAPI

from app.routers import public


def create_app() -> FastAPI:
    app = FastAPI(title="Candidate Assessment Platform")
    app.include_router(public.router)
    return app


app = create_app()
