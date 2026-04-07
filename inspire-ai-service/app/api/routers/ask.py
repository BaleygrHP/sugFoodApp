from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional, List

from app.services.agent import AgentService

ask_router = router = APIRouter(prefix="/ask")


class AskRequest(BaseModel):
    """Simple request schema for asking AI questions"""
    question: str = Field(..., description="Câu hỏi bạn muốn hỏi AI")
    doc_ids: Optional[List[str]] = Field(
        default=None, 
        description="Danh sách document IDs để lọc (tùy chọn). Nếu không có, sẽ tìm trong tất cả documents trong Qdrant"
    )
    top_k: Optional[int] = Field(
        default=5, 
        description="Số lượng documents liên quan nhất để sử dụng (mặc định: 5)"
    )


@router.post("", response_model=dict)
async def ask_ai(
    body: AskRequest, 
    agent_service: AgentService = Depends()
):
    """
    Hỏi AI dựa trên dữ liệu trong Qdrant (RAG)
    
    API đơn giản để hỏi AI về thông tin đã được index trong Qdrant.
    AI sẽ tự động tìm kiếm các documents liên quan và trả lời câu hỏi của bạn.
    
    **Ví dụ:**
    ```json
    {
        "question": "Tổng quan về sản phẩm X là gì?",
        "top_k": 5
    }
    ```
    
    **Response:**
    ```json
    {
        "answer": "Câu trả lời từ AI...",
        "sources": [
            {
                "doc_id": "...",
                "text": "Nội dung liên quan...",
                "score": 0.95
            }
        ]
    }
    ```
    """
    return agent_service.query_knowledge(
        question=body.question,
        doc_ids=body.doc_ids,
        top_k=body.top_k
    )


