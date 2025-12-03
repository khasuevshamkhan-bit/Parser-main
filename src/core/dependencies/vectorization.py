from fastapi import Depends
from src.core.dependencies.allowances import get_allowance_repository
from src.core.dependencies.vector_search import get_allowance_embedding_service, get_vectorizer
from src.repositories.allowance_repository import AllowanceRepository
from src.services.allowance_embedding_service import AllowanceEmbeddingService
from src.services.allowance_vectorization_service import AllowanceVectorizationService
from src.services.embedding_builder import QueryEmbeddingBuilder
from src.services.vectorizer import Vectorizer


async def get_vectorization_service(
        allowance_repository: AllowanceRepository = Depends(get_allowance_repository),
        embedding_service: AllowanceEmbeddingService = Depends(get_allowance_embedding_service),
        vectorizer: Vectorizer = Depends(get_vectorizer),
) -> AllowanceVectorizationService:
    """
    Provide service coordinating vectorization workflows.
    """

    query_builder = QueryEmbeddingBuilder()
    return AllowanceVectorizationService(
        allowance_repository=allowance_repository,
        embedding_service=embedding_service,
        query_builder=query_builder,
        vectorizer=vectorizer,
    )
