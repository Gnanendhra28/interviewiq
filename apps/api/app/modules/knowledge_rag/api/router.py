from fastapi import APIRouter

router = APIRouter()

@router.get("/status")
async def get_knowledge_rag_status():
    return {"module": "knowledge_rag", "status": "active", "description": "Knowledge base document management, chunking & pgvector RAG retrieval"}
