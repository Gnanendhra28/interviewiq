from fastapi import APIRouter

router = APIRouter()

@router.get("/status")
async def get_interviews_status():
    return {"module": "interviews", "status": "active"}
