from fastapi import APIRouter

router = APIRouter()

@router.get("/status")
async def get_audit_status():
    return {"module": "audit_logging", "status": "active"}
