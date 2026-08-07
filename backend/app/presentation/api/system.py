from fastapi import APIRouter, Depends
from app.core.observability import system_monitor
from app.presentation.api.auth import get_current_user_dependency
from app.domain.auth.entities import User as DomainUser

router = APIRouter(prefix="/system", tags=["Monitoring & Observability Engine"])


@router.get("/diagnostics")
async def get_system_diagnostics(
    current_user: DomainUser = Depends(get_current_user_dependency)
):
    """Retrieve host container hardware health levels and application metrics."""
    return system_monitor.get_metrics()
