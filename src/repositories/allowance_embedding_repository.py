from dataclasses import dataclass

from sqlalchemy import Select, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.db.allowance import Allowance
from src.models.db.allowance_embedding import AllowanceEmbedding


@dataclass
class EmbeddingSearchResult:
    """
    Holds an allowance and its similarity score.
    """

    allowance: Allowance
    score: float


class AllowanceEmbeddingRepository:
    """
    Persistence layer for allowance embeddings.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_embedding(self, allowance_id: int, embedding: list[float], model_name: str) -> AllowanceEmbedding:
        """
        Insert or update an allowance embedding.
        """

        statement = (
            pg_insert(AllowanceEmbedding)
            .values(
                allowance_id=allowance_id,
                embedding=embedding,
                embedding_model=model_name,
            )
            .on_conflict_do_update(
                index_elements=[AllowanceEmbedding.allowance_id],
                set_={
                    "embedding": embedding,
                    "embedding_model": model_name,
                },
            )
            .returning(AllowanceEmbedding)
        )

        result = await self._session.execute(statement)
        await self._session.commit()
        return result.scalar_one()

    async def list_allowances_without_embeddings(self) -> list[Allowance]:
        """
        Fetch allowances that do not have stored embeddings.
        """

        statement: Select[tuple[Allowance]] = (
            select(Allowance)
            .join(AllowanceEmbedding, AllowanceEmbedding.allowance_id == Allowance.id, isouter=True)
            .where(AllowanceEmbedding.id.is_(None))
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def search_by_vector(self, embedding: list[float], limit: int) -> list[EmbeddingSearchResult]:
        """
        Retrieve allowances ordered by vector similarity.
        """

        distance = AllowanceEmbedding.embedding.cosine_distance(embedding)
        statement: Select[tuple[Allowance, float]] = (
            select(Allowance, distance.label("score"))
            .join(AllowanceEmbedding, AllowanceEmbedding.allowance_id == Allowance.id)
            .order_by(distance)
            .limit(limit)
        )

        result = await self._session.execute(statement)
        rows = result.all()
        return [EmbeddingSearchResult(allowance=row[0], score=float(row[1])) for row in rows]
