from fastapi import FastAPI

from app.problems import register_problem_handlers
from app.routers import health, reports


def create_app() -> FastAPI:
    app = FastAPI(
        title="DWMS Location Reporting Service",
        version="0.1.0",
        summary="Waste report API (Objective 1, Feature 18). Contract: docs/api/locations.yaml",
    )
    register_problem_handlers(app)
    app.include_router(health.router)
    app.include_router(reports.router)
    return app


app = create_app()
