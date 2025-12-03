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

    The endpoint normalizes questionnaire answers and returns the generated
    embedding for client-side consumption.
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

    The endpoint keeps embedding identifiers aligned with allowance identifiers
    and reports which requested allowances were processed.
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
    Generate embeddings for allowances that lack vector representations.

    Returns the number of newly created embeddings.
    """

    return await vectorization_service.vectorize_missing_allowances()
