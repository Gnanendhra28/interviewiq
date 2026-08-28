from fastapi import APIRouter

router = APIRouter()

@router.get("/status")
async def get_candidates_status():
    return {"module": "candidates", "status": "active"}
