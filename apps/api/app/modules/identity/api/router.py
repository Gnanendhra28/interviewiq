from fastapi import APIRouter

router = APIRouter()

@router.get("/status")
async def get_identity_status():
    return {"module": "identity", "status": "active"}
