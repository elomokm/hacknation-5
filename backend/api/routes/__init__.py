"""API route modules."""

from api.routes.config import router as config_router
from api.routes.health import router as health_router
from api.routes.onboarding import router as onboarding_router
from api.routes.opportunity import router as opportunity_router
from api.routes.profile import router as profile_router
from api.routes.risk import router as risk_router

__all__ = [
    "config_router",
    "health_router",
    "onboarding_router",
    "opportunity_router",
    "profile_router",
    "risk_router",
]
