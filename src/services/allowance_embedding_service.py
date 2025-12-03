from src.models.db.allowance import Allowance
from src.repositories.allowance_embedding_repository import (
    AllowanceEmbeddingRepository,
)
from src.services.embedding_builder import AllowanceEmbeddingBuilder
from src.services.vectorizer import Vectorizer


class AllowanceEmbeddingService:
    """
    Handles creation and maintenance of allowance embeddings.
    """

    def __init__(
            self,
            embedding_repository: AllowanceEmbeddingRepository,
            vectorizer: Vectorizer,
            builder: AllowanceEmbeddingBuilder,
    ) -> None:
        self._embedding_repository = embedding_repository
        self._vectorizer = vectorizer
        self._builder = builder

    async def index_allowance(self, allowance: Allowance) -> None:
        """
        Create or refresh embedding for a single allowance.
        """

        document = self._builder.build_document(
            name=allowance.name,
            npa_name=allowance.npa_name,
            level=allowance.level,
            subjects=allowance.subjects,
            validity_period=allowance.validity_period,
        )

        if not document:
            return

        embedding = await self._vectorizer.embed_text(text=document)
        if not embedding:
            return

        await self._embedding_repository.upsert_embedding(
            allowance_id=allowance.id,
            embedding=embedding,
            model_name=self._vectorizer.model_name,
        )

    async def index_many(self, allowances: list[Allowance]) -> None:
        """
        Generate embeddings for multiple allowances sequentially.
        """

        for allowance in allowances:
            await self.index_allowance(allowance=allowance)

    async def index_missing(self) -> None:
        """
        Populate embeddings for allowances that lack vectors.
        """

        missing_allowances = await self._embedding_repository.list_allowances_without_embeddings()
        if not missing_allowances:
            return

        await self.index_many(allowances=missing_allowances)
