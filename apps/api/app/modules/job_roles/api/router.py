from fastapi import APIRouter

router = APIRouter()

@router.get("/status")
async def get_job_roles_status():
    return {"module": "job_roles", "status": "active"}
