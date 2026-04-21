from fastapi import APIRouter

from app.api.routes import analysis, auth, cases, dashboard, evaluations, health, rubrics

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(cases.router)
api_router.include_router(rubrics.router)
api_router.include_router(evaluations.router)
api_router.include_router(analysis.router)
api_router.include_router(dashboard.router)
