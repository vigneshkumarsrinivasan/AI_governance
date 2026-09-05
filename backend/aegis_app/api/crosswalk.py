"""
Crosswalk Matrix & Evidence Resolution Endpoints.
Visualizes the 17-framework crosswalk and proves multi-framework evidence satisfaction.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from aegis_app.schemas.schemas import CrosswalkControlRow
from aegis_app.services.crosswalk import crosswalk_service
from aegis_app.models.models import User
from aegis_app.api.deps import get_current_user

router = APIRouter(prefix="/crosswalk", tags=["Crosswalk Matrix"])

class ResolveEvidenceInput(BaseModel):
    control_ids: List[str]

@router.get("/matrix", response_model=List[CrosswalkControlRow])
async def get_matrix(current_user: User = Depends(get_current_user)):
    """
    Returns the complete Cross-Framework Crosswalk Matrix,
    mapping Unified Controls to EU AI Act, NIST AI RMF, CRA, OWASP, CSF, etc.
    """
    return crosswalk_service.get_crosswalk_matrix()

@router.post("/resolve-evidence", response_model=Dict[str, Any])
async def resolve_evidence(
    payload: ResolveEvidenceInput,
    current_user: User = Depends(get_current_user)
):
    """
    Given a list of Unified Control IDs, resolves all frameworks and specific requirements
    that are satisfied without duplicating evidence uploads.
    """
    return crosswalk_service.resolve_evidence_coverage(payload.control_ids)
