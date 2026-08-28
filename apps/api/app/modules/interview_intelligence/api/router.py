from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
async def get_interview_intelligence_status():
    return {
        "module": "interview_intelligence",
        "status": "active",
        "description": (
            "Grounded question generation, AI answer evaluation & dynamic "
            "adaptive difficulty engine"
        ),
    }
