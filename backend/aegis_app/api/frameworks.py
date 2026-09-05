"""
Authoritative Framework Catalog Endpoints.
Serves all 17 authoritative frameworks with requirements, chapters,
official references, and legal URLs.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from aegis_app.schemas.schemas import FrameworkSummary
from aegis_app.services.crosswalk import crosswalk_service
from aegis_app.models.models import User
from aegis_app.api.deps import get_current_user

router = APIRouter(prefix="/frameworks", tags=["Frameworks"])

@router.get("", response_model=List[FrameworkSummary])
async def list_frameworks(current_user: User = Depends(get_current_user)):
    """
    Returns summary catalog of all 17 authoritative frameworks loaded in AegisAI.
    """
    return crosswalk_service.get_frameworks_summary()

@router.get("/{framework_id}", response_model=Dict[str, Any])
async def get_framework_detail(
    framework_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Returns complete hierarchical tree for a specific framework:
    Chapters -> Articles -> Normalized Requirements -> Evidence Expected.
    """
    fw = crosswalk_service.get_framework(framework_id)
    if not fw:
        raise HTTPException(status_code=404, detail="Framework not found in catalog")
    return fw
