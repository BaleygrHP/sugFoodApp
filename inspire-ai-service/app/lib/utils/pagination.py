import json
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar

from fastapi import HTTPException
from fastapi import Query as QueryParam
from pydantic import BaseModel, Field
from sqlalchemy import asc, desc, inspect, or_
from sqlalchemy.orm import Query

from app.core.logger import get_logger

from .string import camel_to_snake

logger = get_logger(__name__)


T = TypeVar("T")


class Order(str, Enum):
    ASC = "ASC"
    DESC = "DESC"


class PageOptionsDto(BaseModel):
    query: Optional[str] = None
    query_fields: Optional[List[str]] = None
    order: Order = Field(Order.DESC)
    order_field: Optional[str] = None
    offset: int = Field(0, ge=0)
    limit: int = Field(10, ge=1, le=50)
    filters: Optional[Dict[str, Any]] = None


class PageMetaDto(BaseModel):
    limit: int
    total: int
    offset: int
    has_next: bool


class PageDto(BaseModel, Generic[T]):
    data: List[T]
    meta: PageMetaDto

    class Config:
        arbitrary_types_allowed = True


def get_pagination_params(
    query: Optional[str] = QueryParam(None, description="Search query"),
    query_fields: Optional[List[str]] = QueryParam(None, description="Fields to search in"),
    order: Order = QueryParam(Order.DESC, description="Sort order (ASC or DESC)"),
    order_field: Optional[str] = QueryParam("createdAt", description="Field to sort by"),
    offset: int = QueryParam(0, ge=0, description="Number of items to skip"),
    limit: int = QueryParam(10, ge=1, le=50, description="Number of items per page"),
    filters: Optional[str] = QueryParam(None, description="JSON string of filter criteria, eg: {\"field\": value} or {\"field\": {\"gt\": value}}")
) -> PageOptionsDto:
    """Extract pagination parameters from query parameters"""
    filter_dict = None
    if filters:
        try:
            filter_dict = json.loads(filters)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=422,
                detail="Invalid JSON format in filters parameter"
            )

    return PageOptionsDto(
        query=query,
        query_fields=query_fields,
        order=order,
        order_field=order_field,
        offset=offset,
        limit=limit,
        filters=filter_dict
    )


def get_model_field(model, field_name):
    """
    Resolve a field name to a SQLAlchemy column attribute.
    Handle common naming patterns and search parent classes for fields.
    """
    # Handle direct attribute match
    if hasattr(model, field_name):
        return getattr(model, field_name)

    # Try snake_case version
    snake_case = camel_to_snake(field_name)
    if snake_case != field_name and hasattr(model, snake_case):
        return getattr(model, snake_case)

    # Look in parent classes (for fields from AuditableEntity etc.)
    for base in model.__mro__[1:-1]:
        if hasattr(base, field_name):
            return getattr(model, field_name)
        if snake_case != field_name and hasattr(base, snake_case):
            return getattr(model, snake_case)

    # Use SQLAlchemy inspection as a last resort
    try:
        mapper = inspect(model)
        for column in mapper.columns:
            if column.name == field_name:
                return getattr(model, column.key)
    except Exception:
        pass

    return None


def apply_filters(query: Query, model, filters: Dict[str, Any]) -> Query:
    """
    Apply filter criteria to SQLAlchemy query

    Supports:
    - Simple equality: {"field": value}
    - IN operator: {"field": [value1, value2]}
    - Range comparisons: {"field": {"gt": value}}
    - NULL check: {"field": None}
    """

    if not filters:
        return query

    for field_name, value in filters.items():
        column = get_model_field(model, field_name)
        if not column:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid filter field: {field_name}",
            )

        if value is None:
            query = query.filter(column.is_(None))
        elif isinstance(value, dict):
            for op, op_value in value.items():
                if op == "gt":
                    query = query.filter(column > op_value)
                elif op == "lt":
                    query = query.filter(column < op_value)
                elif op == "gte":
                    query = query.filter(column >= op_value)
                elif op == "lte":
                    query = query.filter(column <= op_value)
                elif op == "eq":
                    query = query.filter(column == op_value)
                elif op == "neq":
                    query = query.filter(column != op_value)
        elif isinstance(value, list):
            query = query.filter(column.in_(value))
        else:
            query = query.filter(column == value)

    return query


def apply_search(query: Query, model, search_term: str, search_field: List[str]) -> Query:
    """
    Apply search term across multiple fiels to SQLAlchemy query
    """
    if not search_term or not search_field:
        return query

    search_conditions = []
    for field_name in search_field:
        column = get_model_field(model, field_name)
        if not column:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid search field: {field_name}",
            )
        if hasattr(column, "ilike"):
            search_conditions.append(column.ilike(f"%{search_term}%"))

    if search_conditions:
        query = query.filter(or_(*search_conditions))

    return query


def generate_pagination_result(
    query: Query,
    page_options: PageOptionsDto,
    model=None,
) -> PageDto:
    """
    Generate paginated results from SQLAlchemy query

    Args:
        query: SQLAlchemy query object
        page_options: Pagination options
        model: SQLAlchemy model (optional, for field validation)

    Returns:
        PageDto with data and metadata
    """
    if page_options.query and page_options.query_fields and model:
        fields_to_search = page_options.query_fields
        if fields_to_search:
            query = apply_search(query, model, page_options.query, fields_to_search)

    if page_options.filters and model:
        query = apply_filters(query, model, page_options.filters)

    total = query.count()

    order_func = desc if page_options.order == Order.DESC else asc
    if page_options.order_field and model:
        column = get_model_field(model, page_options.order_field)

        if column:
            query = query.order_by(order_func(column))
        else:
            for default_field in ["created_at", "createdAt", "id"]:
                default_column = get_model_field(model, default_field)
                if default_column:
                    logger.warning(f"Field '{page_options.order_field}' not found in model '{model.__name__}'. Using default ordering.")
                    query = query.order_by(order_func(default_column))
                    break

    query = query.offset(page_options.offset)
    query = query.limit(page_options.limit)

    entities = query.all()

    meta = PageMetaDto(
        limit=page_options.limit or 10,
        offset=page_options.offset or 0,
        total=total,
        has_next=(page_options.offset or 0) + (page_options.limit or 10) < total,
    )

    return PageDto(data=entities, meta=meta)


def generate_pagination_with_data(
    entities: List[T], total: int, page_options: PageOptionsDto
) -> PageDto[T]:
    """
    Generate pagination result with pre-fetched data

    Args:
        entities: List of entities/data
        total: Total count of items (before pagination)
        page_options: Pagination options

    Returns:
        PageDto with data and metadata
    """
    meta = PageMetaDto(
        limit=page_options.limit or 10,
        offset=page_options.offset or 0,
        total=total,
        has_next=(page_options.offset or 0) + (page_options.limit or 10) < total,
    )

    return PageDto(data=entities, meta=meta)
