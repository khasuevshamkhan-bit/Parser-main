from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.core.database import get_session
from src.repositories.allowance_embedding_repository import AllowanceEmbeddingRepository
from src.services.allowance_embedding_service import AllowanceEmbeddingService
from src.services.embedding_builder import AllowanceEmbeddingBuilder, QueryEmbeddingBuilder
from src.services.vector_search_service import VectorSearchService
from src.services.vectorizer import Vectorizer, create_vectorizer


@lru_cache
def get_vectorizer() -> Vectorizer:
    """
    Provide a singleton vectorizer instance for embedding generation.

    :return: Cached vectorizer instance.
    """

    return create_vectorizer(
        backend=settings.vector.backend,
        model_name=settings.vector.model_name,
        dimension=settings.vector.dimension,
        load_timeout_seconds=settings.vector.load_timeout_seconds,
        offline=settings.vector.offline,
        local_model_path=settings.vector.local_model_path,
    )


async def get_allowance_embedding_service(
        session: AsyncSession = Depends(get_session),
        vectorizer: Vectorizer = Depends(get_vectorizer),
) -> AllowanceEmbeddingService:
    """
    Dependency injector for embedding service.

    :param session: Active database session.
    :param vectorizer: Vectorizer dependency.
    :return: Configured embedding service.
    """

    embedding_repository = AllowanceEmbeddingRepository(session=session)
    builder = AllowanceEmbeddingBuilder()
    return AllowanceEmbeddingService(
        embedding_repository=embedding_repository,
        vectorizer=vectorizer,
        builder=builder,
    )


async def get_vector_search_service(
        session: AsyncSession = Depends(get_session),
        vectorizer: Vectorizer = Depends(get_vectorizer),
) -> VectorSearchService:
    """
    Dependency injector for semantic search service.

    :param session: Active database session.
    :param vectorizer: Vectorizer dependency.
    :return: Configured vector search service.
    """

    embedding_repository = AllowanceEmbeddingRepository(session=session)
    embedding_service = AllowanceEmbeddingService(
        embedding_repository=embedding_repository,
        vectorizer=vectorizer,
        builder=AllowanceEmbeddingBuilder(),
    )
    query_builder = QueryEmbeddingBuilder()
    return VectorSearchService(
        embedding_repository=embedding_repository,
        vectorizer=vectorizer,
        query_builder=query_builder,
        embedding_service=embedding_service,
    )
