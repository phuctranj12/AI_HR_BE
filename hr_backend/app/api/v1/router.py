from fastapi import APIRouter

from app.api.v1.endpoints import catalog, documents, employees, faces, health, persons, projects

router = APIRouter(prefix="/api/v1")

router.include_router(health.router)
router.include_router(catalog.router)
router.include_router(documents.router)
router.include_router(employees.router)
router.include_router(faces.router)
router.include_router(persons.router)
router.include_router(projects.router)

