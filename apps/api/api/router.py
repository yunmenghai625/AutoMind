from fastapi import APIRouter

from apps.api.api.routes import (
    admin,
    aigc,
    auth,
    chat,
    diagnosis,
    feedback,
    garage,
    health,
    knowledge,
    preferences,
    telemetry,
    vehicle,
    vehicle_data,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["system"])
api_router.include_router(vehicle.router, prefix="/vehicle", tags=["vehicle"])
api_router.include_router(chat.router, prefix="/chat", tags=["agent"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(aigc.router, prefix="/aigc", tags=["aigc"])
api_router.include_router(diagnosis.router, prefix="/diagnosis", tags=["diagnosis"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(preferences.router, prefix="/preferences", tags=["memory"])
api_router.include_router(garage.router, prefix="/garage", tags=["garage"])
api_router.include_router(vehicle_data.router, prefix="/vehicle", tags=["vehicle-data"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
api_router.include_router(telemetry.router, prefix="/telemetry", tags=["telemetry"])
