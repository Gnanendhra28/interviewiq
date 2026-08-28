from fastapi import APIRouter

router = APIRouter()

@router.get("/status")
async def get_reports_status():
    return {"module": "reports", "status": "active"}
