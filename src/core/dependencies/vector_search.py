from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.core.database import get_session
from src.repositories.allowance_embedding_repository import AllowanceEmbeddingRepository
from src.services.allowance_embedding_service import AllowanceEmbeddingService
from src.services.embedding_builder import AllowanceEmbeddingBuilder, QueryEmbeddingBuilder
from src.services.reranker import CrossEncoderReranker
from src.services.vector_search_service import VectorSearchService
from src.services.vectorizer import Vectorizer, create_vectorizer


@lru_cache
def get_vectorizer() -> Vectorizer:
    """
    Provide a singleton vectorizer instance for embedding generation.
    """

    return create_vectorizer(
        backend=settings.vector.backend,
        model_name=settings.vector.model_name,
        dimension=settings.vector.dimension,
        load_timeout_seconds=settings.vector.load_timeout_seconds,
        offline=settings.vector.offline,
        local_model_path=settings.vector.local_model_path,
    )


@lru_cache
def get_reranker() -> CrossEncoderReranker | None:
    """
    Provide a singleton reranker when enabled in configuration.
    """

    if not settings.vector.enable_rerank:
        return None
    return CrossEncoderReranker(
        model_name=settings.vector.rerank_model_name,
        load_timeout_seconds=settings.vector.load_timeout_seconds,
    )


async def get_allowance_embedding_service(
        session: AsyncSession = Depends(get_session),
        vectorizer: Vectorizer = Depends(get_vectorizer),
) -> AllowanceEmbeddingService:
    """
    Dependency injector for embedding service.
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
        reranker: CrossEncoderReranker | None = Depends(get_reranker),
) -> VectorSearchService:
    """
    Dependency injector for semantic search service.
    """

    embedding_repository = AllowanceEmbeddingRepository(session=session)
    embedding_service = AllowanceEmbeddingService(
        embedding_repository=embedding_repository,
        vectorizer=vectorizer,
        builder=AllowanceEmbeddingBuilder(),
    )
    query_builder = QueryEmbeddingBuilder()
    document_builder = AllowanceEmbeddingBuilder()
    return VectorSearchService(
        embedding_repository=embedding_repository,
        vectorizer=vectorizer,
        query_builder=query_builder,
        embedding_service=embedding_service,
        document_builder=document_builder,
        reranker=reranker,
    )
