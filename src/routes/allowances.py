from fastapi import APIRouter, Depends, Query

from src.core.dependencies.allowances import get_allowance_service
from src.core.dependencies.vector_search import get_vector_search_service
from src.core.dependencies.parsers import get_domrf_parser
from src.models.dto.allowances import AllowanceCreateDTO, AllowanceDTO
from src.models.dto.vector_search import InputFormDTO, VectorSearchResultDTO
from src.parsers.domrf import DomRfParser
from src.services.allowance_service import AllowanceService
from src.services.vector_search_service import VectorSearchService

router = APIRouter(prefix="/allowances", tags=["Allowances"])


@router.get("", summary="List allowances", response_model=list[AllowanceDTO])
async def list_allowances(
        allowance_service: AllowanceService = Depends(get_allowance_service),
) -> list[AllowanceDTO]:
    """
    Retrieve all stored allowances.

    :return: collection of allowances
    """

    return await allowance_service.list_allowances()


@router.post("", summary="Create allowance", response_model=AllowanceDTO)
async def create_allowance(
        payload: AllowanceCreateDTO, allowance_service: AllowanceService = Depends(get_allowance_service)
) -> AllowanceDTO:
    """
    Persist a new allowance.

    :return: created allowance
    """

    return await allowance_service.create_allowance(payload=payload)


@router.post("/parse/domrf", summary="Parse Dom.rf", response_model=list[AllowanceDTO])
async def parse_domrf(
        max_items: int | None = Query(
            default=None,
            ge=1,
            le=1000,
            description="Maximum number of programs to parse (for testing)",
        ),
        allowance_service: AllowanceService = Depends(get_allowance_service),
        parser: DomRfParser = Depends(get_domrf_parser),
) -> list[AllowanceDTO]:
    """
    Run Dom.rf parser and replace stored allowances.

    :return: parsed allowances persisted to storage
    """

    if max_items is not None:
        parser.set_max_items(limit=max_items)

    return await allowance_service.parse_and_replace(parser=parser)


@router.post("/vector-search", summary="Find allowances via semantic similarity", response_model=list[VectorSearchResultDTO])
async def vector_search(
        payload: InputFormDTO,
        limit: int | None = Query(
            default=None,
            ge=1,
            le=50,
            description="Maximum number of results to return",
        ),
        search_service: VectorSearchService = Depends(get_vector_search_service),
) -> list[VectorSearchResultDTO]:
    """
    Run semantic similarity search based on questionnaire text.
    """

    return await search_service.search(query_text=payload.input, limit=limit)
