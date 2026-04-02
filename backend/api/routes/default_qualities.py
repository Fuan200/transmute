from fastapi import APIRouter, Depends, HTTPException
from db import DefaultQualitiesDB
from api.deps import get_current_active_user, get_default_qualities_db
from api.schemas import DefaultQualityMapping, DefaultQualityListResponse

router = APIRouter(prefix="/default-qualities", tags=["default-qualities"])

@router.get(
    "",
    summary="Get all default quality mappings",
    responses={
        200: {
            "model": DefaultQualityListResponse,
            "description": "List of default quality mappings"
        }
    }
)
def get_default_qualities(
    db: DefaultQualitiesDB = Depends(get_default_qualities_db),
    current_user: dict = Depends(get_current_active_user),
):
    """Return all user-configured default quality mappings."""
    return {"defaults": db.get_all(current_user["uuid"])}

@router.put(
    "",
    summary="Set a default quality mapping",
    responses={
        200: {
            "model": DefaultQualityMapping,
            "description": "The created or updated mapping"
        }
    }
)
def upsert_default_quality(
    mapping: DefaultQualityMapping,
    db: DefaultQualitiesDB = Depends(get_default_qualities_db),
    current_user: dict = Depends(get_current_active_user),
):
    """Create or update a default quality for a given output format."""
    return db.upsert(current_user["uuid"], mapping.output_format, mapping.quality)

@router.delete(
    "/{output_format}",
    summary="Delete a default quality mapping",
    responses={
        200: {"description": "Mapping deleted"},
        404: {"description": "Mapping not found"}
    }
)
def delete_default_quality(
    output_format: str,
    db: DefaultQualitiesDB = Depends(get_default_qualities_db),
    current_user: dict = Depends(get_current_active_user),
):
    """Remove a default quality mapping for the given output format."""
    if not db.delete(current_user["uuid"], output_format):
        raise HTTPException(status_code=404, detail=f"No default quality for '{output_format}'")
    return {"message": f"Default quality for '{output_format}' deleted"}
