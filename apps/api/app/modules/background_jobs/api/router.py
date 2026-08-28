from fastapi import APIRouter

router = APIRouter()

@router.get("/status")
async def get_jobs_status():
    return {"module": "background_jobs", "status": "active"}
