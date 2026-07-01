from fastapi import APIRouter

from app.api.v1.routers import auth_routes, tasks_routes, project_routes

router_v1 = APIRouter(prefix="/api/v1")


router_v1.include_router(auth_routes.router, prefix="/auth")
router_v1.include_router(tasks_routes.router, prefix="/projects/{project_public_id}/tasks")
router_v1.include_router(project_routes.router, prefix="/projects")
