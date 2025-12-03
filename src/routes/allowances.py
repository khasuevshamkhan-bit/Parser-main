from fastapi import APIRouter, Depends, Query

from src.core.dependencies.allowances import (
    get_allowance_service,
    get_allowance_service_with_embeddings,
)
from src.core.dependencies.parsers import get_domrf_parser
from src.core.dependencies.vector_search import get_vector_search_service
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
    Retrieve every allowance currently persisted in storage.

    The endpoint delegates the read operation to the allowance service, which
    queries the repository for all records and converts them into DTO objects
    for response serialization.

    :param allowance_service: service that loads allowances from the
        persistence layer.
    :return: collection of stored allowances.
    """

    return await allowance_service.list_allowances()


@router.post("", summary="Create allowance", response_model=AllowanceDTO)
async def create_allowance(
        payload: AllowanceCreateDTO,
        allowance_service: AllowanceService = Depends(get_allowance_service_with_embeddings),
) -> AllowanceDTO:
    """
    Persist a new allowance and align its embedding.

    The endpoint cleans incoming payload fields, validates required values, and
    persists the allowance via the service. When embedding support is enabled,
    the created allowance is immediately indexed so that vector search remains
    in sync with the primary datastore.

    :param payload: allowance definition to store and index.
    :param allowance_service: service that validates, persists, and indexes the
        allowance.
    :return: newly created allowance with its database identifier.
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
        allowance_service: AllowanceService = Depends(get_allowance_service_with_embeddings),
        parser: DomRfParser = Depends(get_domrf_parser),
) -> list[AllowanceDTO]:
    """
    Parse Dom.rf source data and replace stored allowances with fresh results.

    The endpoint optionally limits how many programs the parser processes, then
    runs the parser asynchronously with a safety timeout. Successfully parsed
    allowances replace only missing records in storage, and each persisted
    allowance is immediately re-indexed to keep embeddings consistent.

    :param max_items: optional cap on programs fetched from Dom.rf for testing
        or throttling.
    :param allowance_service: service orchestrating storage updates and
        embedding synchronization.
    :param parser: Dom.rf parser instance that scrapes and normalizes source
        programs.
    :return: list of newly stored allowances produced by the parse.
    """

    if max_items is not None:
        parser.set_max_items(limit=max_items)

    return await allowance_service.parse_and_replace(parser=parser)


@router.post("/vector-search", summary="Find allowances via semantic similarity",
             response_model=list[VectorSearchResultDTO])
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
    Execute semantic similarity search backed by synchronized embeddings.

    The endpoint normalizes questionnaire input, ensures embeddings exist for
    all allowances, builds a query embedding, and queries the vector index with
    the configured similarity metric. Results are filtered by score, optionally
    reranked with a cross-encoder, and returned in descending relevance order
    with allowance identifiers and names.

    :param payload: questionnaire input used to build the query embedding.
    :param limit: optional cap on the number of matched allowances to return.
    :param search_service: service that orchestrates embedding lookup, scoring,
        filtering, and reranking.
    :return: ordered list of allowance matches with similarity scores.
    """

    return await search_service.search(query_text=payload.input, limit=limit)
