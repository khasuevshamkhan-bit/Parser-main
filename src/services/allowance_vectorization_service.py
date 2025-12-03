from src.core.exceptions.embeddings import (
    EmbeddingNotFoundError,
    EmbeddingProcessingError,
    EmbeddingValidationError,
)
from src.models.dto.vector_search import AllowanceVectorizeResultDTO
from src.repositories.allowance_repository import AllowanceRepository
from src.services.allowance_embedding_service import AllowanceEmbeddingService
from src.services.embedding_builder import QueryEmbeddingBuilder
from src.services.vectorizer import Vectorizer
from src.utils.logger import logger


class AllowanceVectorizationService:
    """
    Coordinate embedding workflows for questionnaire input and allowances.
    """

    def __init__(
            self,
            allowance_repository: AllowanceRepository,
            embedding_service: AllowanceEmbeddingService,
            query_builder: QueryEmbeddingBuilder,
            vectorizer: Vectorizer,
    ) -> None:
        self._allowance_repository = allowance_repository
        self._embedding_service = embedding_service
        self._query_builder = query_builder
        self._vectorizer = vectorizer

    async def vectorize_user_input(self, user_input: str) -> list[float]:
        """
        Build an embedding for normalized questionnaire input.

        The method validates the incoming text, normalizes it, and forwards it to
        the shared vectorizer. Validation failures and vectorizer errors are
        converted into HTTP-friendly embedding exceptions.
        """

        logger.info("Vectorizing user input for semantic workflows")
        normalized = self._query_builder.build_query(user_input=user_input)
        if not normalized:
            raise EmbeddingValidationError(detail="User input is empty after normalization.")

        try:
            embedding = await self._vectorizer.embed_text(text=normalized)
        except Exception as exc:  # noqa: BLE001
            raise EmbeddingProcessingError(detail="Failed to vectorize user input.") from exc

        if not embedding:
            raise EmbeddingProcessingError(detail="Vectorizer returned an empty embedding.")

        logger.info(
            message=(
                f"User input vectorization completed using model '{self._vectorizer.model_name}'"
            )
        )
        return embedding

    async def vectorize_allowances(self, allowance_ids: list[int]) -> AllowanceVectorizeResultDTO:
        """
        Generate embeddings for provided allowances and report progress.

        The method fails fast when the payload is empty, raises a not-found error
        when no allowances match supplied identifiers, and wraps embedding
        failures into processing errors while keeping allowance identifiers in
        sync with their embeddings.
        """

        if not allowance_ids:
            raise EmbeddingValidationError(detail="Allowance identifiers are required for vectorization.")

        allowances = await self._allowance_repository.list_by_ids(ids=allowance_ids)
        if not allowances:
            raise EmbeddingNotFoundError(detail="No allowances found for the provided identifiers.")

        processed_ids: list[int] = []
        for allowance in allowances:
            try:
                await self._embedding_service.index_allowance(allowance=allowance)
            except Exception as exc:  # noqa: BLE001
                raise EmbeddingProcessingError(
                    detail=f"Failed to create embedding for allowance id={allowance.id}.",
                ) from exc
            processed_ids.append(allowance.id)

        missing_ids = [allowance_id for allowance_id in allowance_ids if allowance_id not in processed_ids]
        return AllowanceVectorizeResultDTO(processed_ids=processed_ids, missing_ids=missing_ids)

    async def vectorize_missing_allowances(self) -> int:
        """
        Create embeddings for allowances that do not have vectors yet.

        The method surfaces not-found errors when all allowances already have
        embeddings so that clients can distinguish between no-op runs and
        successful indexing passes.
        """

        created = await self._embedding_service.index_missing()
        if created == 0:
            raise EmbeddingNotFoundError(detail="No allowances without embeddings were found.")

        return created
