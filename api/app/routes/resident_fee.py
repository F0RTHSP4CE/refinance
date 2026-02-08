"""ResidentFee routes"""

from app.dependencies.services import get_resident_fee_service
from app.schemas.resident_fee import ResidentFeeFiltersSchema, ResidentFeeSchema
from app.services.resident_fee import ResidentFeeService
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/resident_fees", tags=["Resident Fees"])


@router.get("/", response_model=list[ResidentFeeSchema])
def get_resident_fees(
    filters: ResidentFeeFiltersSchema = Depends(),
    service: ResidentFeeService = Depends(get_resident_fee_service),
):
    return service.get_fees(filters)
