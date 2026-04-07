from typing import Annotated

from fastapi import APIRouter, Body, Depends

from app.schemas.knowledge_extractor import (
    TriggerRulesExtractionDto,
)
from app.services.knowledge_extractor import KnowledgeExtractorService

knowledge_extractor_router = router = APIRouter(prefix="/knowledge-extractor")


@router.post("/trigger-rules-extraction")
def trigger_rules_extraction(
    body: Annotated[TriggerRulesExtractionDto, Body(...)],
    knowledge_extractor_service: Annotated[KnowledgeExtractorService, Depends()],
) -> dict:
    return knowledge_extractor_service.extract_rules_from_histories(
        extraction_session_id=body.extraction_session_id,
        tenant_id=body.tenant_id,
        language=body.language,
    )
