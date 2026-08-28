from fastapi import APIRouter

router = APIRouter()

@router.get("/status")
async def get_org_status():
    return {"module": "organizations", "status": "active"}
