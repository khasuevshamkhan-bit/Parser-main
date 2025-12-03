from src.config import settings
from src.models.dto.vector_search import VectorSearchResultDTO
from src.repositories.allowance_embedding_repository import (
    AllowanceEmbeddingRepository,
    EmbeddingSearchResult,
)
from src.services.allowance_embedding_service import AllowanceEmbeddingService
from src.services.embedding_builder import QueryEmbeddingBuilder
from src.services.vectorizer import Vectorizer


class VectorSearchService:
    """
    Executes semantic search over allowance embeddings.
    """

    def __init__(
            self,
            embedding_repository: AllowanceEmbeddingRepository,
            vectorizer: Vectorizer,
            query_builder: QueryEmbeddingBuilder,
            embedding_service: AllowanceEmbeddingService,
    ) -> None:
        self._embedding_repository = embedding_repository
        self._vectorizer = vectorizer
        self._query_builder = query_builder
        self._embedding_service = embedding_service
        self._default_limit = settings.vector.search_limit

    @property
    def default_limit(self) -> int:
        """
        Return the configured default search limit.
        """

        return self._default_limit

    async def search(
            self,
            query_text: str,
            limit: int | None = None
    ) -> list[VectorSearchResultDTO]:
        """
        Perform a vector similarity search using questionnaire text.
        """

        await self._embedding_service.index_missing()

        normalized_query = self._query_builder.build_query(user_input=query_text)
        if not normalized_query:
            return []

        vector = await self._vectorizer.embed_text(text=normalized_query)
        if not vector:
            return []

        matches = await self._embedding_repository.search_by_vector(
            embedding=vector,
            limit=limit or self._default_limit,
        )
        return [self._to_dto(match=match) for match in matches]

    @staticmethod
    def _to_dto(match: EmbeddingSearchResult) -> VectorSearchResultDTO:
        """
        Convert search result into API response object.
        """

        return VectorSearchResultDTO(
            allowance_id=match.allowance.id,
            allowance_name=match.allowance.name,
            score=match.score,
        )
