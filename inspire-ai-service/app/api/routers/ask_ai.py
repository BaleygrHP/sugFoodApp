from fastapi import APIRouter, Depends, Header
from typing import Optional

from app.models.ask_ai.variable import ApiVariableParseOutput
from app.schemas.ask_ai.formalize_response import FormalizeResponseDto
from app.schemas.ask_ai.parse_api_variables import ParseApiVariablesDto
from app.schemas.ask_ai.ticket_analyze import TicketAnalyzeDto
from app.services.ask_ai.ask_ai import AskAIService
from app.schemas.ask_ai.draft_response import DraftResponseDto
from app.core.tools.query_engine import get_query_engine
from app.schemas.ask_ai.ticket_analyze import TicketAnalyzeResponse
from app.schemas.ask_ai.auto_response import AutoResponseDto, AutoResponseResultDto

ask_ai_router = router = APIRouter(prefix="/ask-ai")

@router.post("/draft-response")
async def draft_response(
    schema: DraftResponseDto,
    service: AskAIService = Depends(),
    query_engine = Depends(get_query_engine),
    x_task_id: Optional[str] = Header(None),
    x_tenant_id: Optional[str] = Header(None),
):
    """
    Generate draft response either synchronously or in background.

    - If X-Task-Id and X-Tenant-Id headers are provided, runs as background task
    - Otherwise, runs synchronously and returns response immediately
    """
    # Background mode: enqueue task and return task info
    if x_task_id and x_tenant_id:
        return service.draft_response_background(
            task_id=x_task_id,
            tenant_id=x_tenant_id,
            data=schema
        )

    # Synchronous mode: return response immediately
    result = await service.draft_response(data=schema, query_engine=query_engine)
    return result

@router.post("/auto-response", response_model=AutoResponseResultDto)
async def auto_response(schema: AutoResponseDto, service: AskAIService = Depends(), query_engine = Depends(get_query_engine)):
    return await service.auto_response(data=schema, query_engine=query_engine)

@router.post("/correct-spelling", response_model=str)
def correct_spelling(schema: FormalizeResponseDto, service: AskAIService = Depends()):
    return service.correct_spelling(data=schema)

@router.post("/simplify-words", response_model=str)
def simplify_words(schema: FormalizeResponseDto, service: AskAIService = Depends()):
    return service.simplify_words(data=schema)

@router.post("/shorten-response", response_model=str)
def shorten_response(schema: FormalizeResponseDto, service: AskAIService = Depends()):
    return service.shorten_response(data=schema)

@router.post("/lengthen-response", response_model=str)
async def lengthen_response(schema: FormalizeResponseDto, service: AskAIService = Depends(), query_engine = Depends(get_query_engine)):
    return await service.lengthen_response(data=schema, query_engine=query_engine)

@router.post("/more-casual", response_model=str)
def more_casual(schema: FormalizeResponseDto, service: AskAIService = Depends()):
    return service.more_casual(data=schema)

@router.post("/more-professional", response_model=str)
def more_professional(schema: FormalizeResponseDto, service: AskAIService = Depends()):
    return service.more_professional(data=schema)

@router.post("/ticket-analyze", response_model=TicketAnalyzeResponse)
def ticket_analyze(schema: TicketAnalyzeDto, service: AskAIService = Depends()):
    return service.ticket_analyze(data=schema)

@router.post("/parse-api-variables", response_model=ApiVariableParseOutput)
def parse_api_variables(schema: ParseApiVariablesDto, service: AskAIService = Depends()):
    return service.parse_api_variables(data=schema)

@router.post("/resolution-summary")
async def generate_resolution_summary(request: dict, service: AskAIService = Depends()):
    return await service.generate_resolution_summary(data=request)
