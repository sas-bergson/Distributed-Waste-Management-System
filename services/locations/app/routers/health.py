from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.repository import Repository

router = APIRouter(tags=["health"])


@router.get("/healthz")
@router.get("/health", include_in_schema=False)  # docker-compose PR #15 still probes /health
def health(repo: Repository) -> JSONResponse:
    up = repo.ping()
    return JSONResponse(
        {
            "status": "ok" if up else "degraded",
            "service": "locations",
            "database": "reachable" if up else "unreachable",
        },
        status_code=200 if up else 503,
    )
