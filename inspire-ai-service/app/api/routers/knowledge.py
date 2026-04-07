import json
from typing import Annotated, List

from fastapi import APIRouter, Depends, Form, UploadFile, Body, HTTPException

from app.schemas.knowledge import ImportDatabaseQueryDto, DeleteDocumentsDto, ImportWebDto, ImportWholeSitesWebDto, QueryKnowledgeDto, ReindexWebDto, ImportProductsDto, GetLatestRevisionDto, ReindexDatabaseQueryDto
from app.services.knowledge import KnowledgeService
from app.services.agent import AgentService
from app.schemas.datasource import GoogleDriveData
from app.core.logger import get_logger

knowledge_router = router = APIRouter(prefix="/knowledge")

logger = get_logger(__name__)

@router.post("/import-file", response_model=dict)
async def import_local_file(file: UploadFile, metadata: Annotated[str | None, Form()] = None, service: KnowledgeService = Depends()):
    """
    Upload and import a file into the knowledge base.
    """
    metadata_dict = {}
    if metadata:
        try:
            metadata_dict = json.loads(metadata)
        except json.JSONDecodeError:
            metadata_dict = {"error": "Invalid metadata format"}

    return await service.import_local_file(file, metadata_dict)


@router.post("/import-web", response_model=dict)
def import_web(body: ImportWebDto, service: KnowledgeService = Depends()):
    """
    Import a web page into the knowledge base.
    """
    return service.import_web(body.web_url, body.metadata)

@router.post("/import-web/whole-sites", response_model=dict)
def import_whole_sites(body: ImportWholeSitesWebDto, service: KnowledgeService = Depends()):
    """
    Import a whole website into the knowledge base.
    """
    return service.import_whole_sites(body.tenant_id, body.web_url, body.metadata, body.max_pages)


@router.delete("/delete-documents", response_model=dict)
async def delete_documents(body: DeleteDocumentsDto, service: KnowledgeService = Depends()):
    """
    Delete documents from the vector store by their IDs.
    """
    return service.delete_documents(body.ref_doc_ids, body.file_paths)

@router.post("/google-drive", response_model=dict)
def import_google_drive(
    drive_data: GoogleDriveData = Body(...),
    service: KnowledgeService = Depends()
):
    """
    Import a single file or folder from Google Drive into the knowledge base.

    This endpoint allows you to import a single file or folder from Google Drive and index it for AI querying.
    The imported content will be processed, indexed, and made available through
    the regular knowledge query endpoints.

    Required parameters:
    - credentials: Authentication details including:
      - access_token: OAuth access token for Google Drive
      - refresh_token, client_id, client_secret: For token refresh
    - config.include_paths: The ID of the file to import from Google Drive

    Optional parameters:
    - metadata: Additional metadata to store with documents

    Returns:
        Dictionary with import results including document IDs for future reference.
    """
    try:
        result = service.import_google_drive(drive_data)
        return result
    except Exception as e:
        logger.error(f"Error processing Google Drive import: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query", response_model=dict)
async def query_knowledge(body: QueryKnowledgeDto, agent_service: AgentService = Depends()):
    """
    Query the knowledge base with a question.

    This endpoint allows you to ask questions about imported knowledge.
    You can optionally filter by specific document IDs.

    Returns:
        A dictionary containing the answer and source information.
    """
    return agent_service.query_knowledge(
        question=body.query,
        doc_ids=body.ref_doc_ids,
        top_k=body.top_k
    )

@router.post("/reindex-web", response_model=dict)
async def reindex_web(body: ReindexWebDto, service: KnowledgeService = Depends()):
    """
    Reindex a web page into the knowledge base.
    """
    return service.reindex_web(body.web_url, body.previous_doc_ids, body.metadata)

@router.post("/import-products", response_model=dict)
async def import_products(body: ImportProductsDto, service: KnowledgeService = Depends()):
  """
  Import products into the knowledge base.
  """
  return service.import_products(body.items, body.platform)

@router.post("/google-drive/revision", response_model=dict)
def get_latest_revision(body: GetLatestRevisionDto, service: KnowledgeService = Depends()):
    """
    Get the latest revision of a Google Drive file.

    This endpoint allows you to check if a Google Drive file has been updated
    by comparing its latest revision with a previously known revision.

    Required parameters:
    - resource_id: The ID of the Google Drive file to check
    - access_token: OAuth access token for Google Drive
    - refresh_token: OAuth refresh token for Google Drive

    Returns:
        Dictionary containing:
        - hasNewRevision: bool indicating if there's a new revision
        - revision: str (if hasNewRevision is True)
        - newAccessToken: str (if token was refreshed)
    """
    try:
        result = service.get_latest_revision(
            file_id=body.file_id,
            credentials={
                "accessToken": body.access_token,
                "refreshToken": body.refresh_token
            }
        )
        return result
    except Exception as e:
        logger.error(f"Error getting latest revision: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import-database-query", response_model=dict)
async def import_database_query(body: ImportDatabaseQueryDto, service: KnowledgeService = Depends()):
  """
  Import data from database query into the knowledge base.
  """
  return service.import_database_query(query=body.query, uri=body.uri, metadata=body.metadata)

@router.post("/reindex-database-query", response_model=dict)
async def reindex_database_query(body: ReindexDatabaseQueryDto, service: KnowledgeService = Depends()):
    """
    Reindex a web page into the knowledge base.
    """
    return service.reindex_database_query(
        query=body.query,
        uri=body.uri,
        previous_doc_ids=body.previous_doc_ids,
        metadata=body.metadata
    )

@router.post("/test-database-query", response_model=list)
async def test_database_query(body: ImportDatabaseQueryDto, service: KnowledgeService = Depends()):
  """
  Import data from database query into the knowledge base.
  """
  return service.test_database_query(query=body.query, uri=body.uri)
