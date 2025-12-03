from fastapi import Depends

from src.core.dependencies.allowances import get_allowance_repository
from src.repositories.allowance_repository import AllowanceRepository
from src.services.vector_search_service import VectorSearchService


def get_vector_search_service(
    repository: AllowanceRepository = Depends(get_allowance_repository),
) -> VectorSearchService:
    """Provide configured vector search service."""

    return VectorSearchService(repository=repository)
