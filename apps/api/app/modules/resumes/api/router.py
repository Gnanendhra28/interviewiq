from fastapi import APIRouter

router = APIRouter()

@router.get("/status")
async def get_resumes_status():
    return {"module": "resumes", "status": "active"}
