from fastapi import APIRouter, Depends

from src.core.dependencies.vectorization import get_vectorization_service
from src.models.dto.vector_search import (
    AllowanceVectorizeRequestDTO,
    AllowanceVectorizeResultDTO,
    InputFormDTO,
    VectorDTO,
)
from src.services.allowance_vectorization_service import AllowanceVectorizationService

router = APIRouter(prefix="/embeddings", tags=["Embeddings"])


@router.post("/input", summary="Vectorize questionnaire input", response_model=VectorDTO)
async def vectorize_input(
        payload: InputFormDTO,
        vectorization_service: AllowanceVectorizationService = Depends(get_vectorization_service),
) -> VectorDTO:
    """
    Build an embedding vector from questionnaire text.

    The endpoint normalizes questionnaire answers, formats them for the E5
    encoder, generates an embedding with the configured vectorizer, and returns
    the normalized vector so the client can preview or reuse it.

    :param payload: questionnaire text provided by the caller.
    :param vectorization_service: service that prepares input and queries the
        vectorizer.
    :return: embedding vector derived from the questionnaire input.
    """

    embedding = await vectorization_service.vectorize_user_input(user_input=payload.input)
    return VectorDTO(embedding=embedding)


@router.post(
    "/allowances",
    summary="Vectorize allowances by id",
    response_model=AllowanceVectorizeResultDTO,
)
async def vectorize_allowances(
        payload: AllowanceVectorizeRequestDTO,
        vectorization_service: AllowanceVectorizationService = Depends(get_vectorization_service),
) -> AllowanceVectorizeResultDTO:
    """
    Create or refresh embeddings for specific allowances.

    The endpoint validates requested allowance identifiers, rebuilds their
    document passages, creates normalized embeddings through the configured
    vectorizer, and upserts the vectors so that semantic search stays
    consistent. The response reports which allowances were processed.

    :param payload: allowance identifiers that must be re-embedded.
    :param vectorization_service: service handling document preparation and
        embedding persistence.
    :return: summary of processed allowances and their embeddings.
    """

    return await vectorization_service.vectorize_allowances(allowance_ids=payload.allowance_ids)


@router.post(
    "/allowances/missing",
    summary="Vectorize missing allowances",
    response_model=int,
)
async def vectorize_missing_allowances(
        vectorization_service: AllowanceVectorizationService = Depends(get_vectorization_service),
) -> int:
    """
    Generate embeddings for allowances that currently lack vector
    representations.

    The endpoint scans stored allowances for missing embeddings, rebuilds their
    document passages, and writes normalized vectors to the embedding store. It
    reports how many embeddings were created.

    :param vectorization_service: service that reconciles stored allowances with
        existing embeddings and persists any missing ones.
    :return: count of embeddings generated during this invocation.
    """

    return await vectorization_service.vectorize_missing_allowances()
