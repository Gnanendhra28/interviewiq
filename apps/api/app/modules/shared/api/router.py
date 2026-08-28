from fastapi import APIRouter

router = APIRouter()

@router.get("/status")
async def get_shared_status():
    return {"module": "shared", "status": "active"}
