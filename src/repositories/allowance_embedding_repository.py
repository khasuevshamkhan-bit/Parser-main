from dataclasses import dataclass

from sqlalchemy import Select, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.db.allowance import Allowance
from src.models.db.allowance_embedding import AllowanceEmbedding


@dataclass
class EmbeddingSearchResult:
    """
    Represents a single allowance matched by vector similarity.
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

    async def search_by_vector(self, embedding: list[float], limit: int, metric: str) -> list[EmbeddingSearchResult]:
        """
        Retrieve allowances ordered by the chosen distance or similarity metric.
        """

        normalized_metric = metric.lower()
        if normalized_metric in {"cosine", "cos"}:
            distance = AllowanceEmbedding.embedding.cosine_distance(embedding)
            statement: Select[tuple[Allowance, float]] = (
                select(Allowance, distance.label("distance"))
                .join(AllowanceEmbedding, AllowanceEmbedding.allowance_id == Allowance.id)
                .order_by(distance)
                .limit(limit)
            )
            return await self._to_results_from_distance(statement=statement)

        if normalized_metric in {"dot", "inner_product"}:
            similarity = AllowanceEmbedding.embedding.max_inner_product(embedding)
            statement: Select[tuple[Allowance, float]] = (
                select(Allowance, similarity.label("similarity"))
                .join(AllowanceEmbedding, AllowanceEmbedding.allowance_id == Allowance.id)
                .order_by(similarity.desc())
                .limit(limit)
            )
            return await self._to_results_from_similarity(statement=statement)

        if normalized_metric in {"l2", "euclidean"}:
            distance = AllowanceEmbedding.embedding.l2_distance(embedding)
            statement: Select[tuple[Allowance, float]] = (
                select(Allowance, distance.label("distance"))
                .join(AllowanceEmbedding, AllowanceEmbedding.allowance_id == Allowance.id)
                .order_by(distance)
                .limit(limit)
            )
            return await self._to_results_from_distance(statement=statement, normalize_l2=True)

        raise ValueError(f"Unsupported search metric '{metric}'. Use cosine, dot, or l2.")

    async def _to_results_from_distance(self, statement: Select, normalize_l2: bool = False) -> list[EmbeddingSearchResult]:
        result = await self._session.execute(statement)
        rows = result.all()
        results: list[EmbeddingSearchResult] = []
        for row in rows:
            distance_value = float(row[1])
            similarity = 1.0 / (1.0 + distance_value) if normalize_l2 else 1.0 - distance_value
            results.append(
                EmbeddingSearchResult(
                    allowance=row[0],
                    score=self._clamp_similarity(value=similarity),
                )
            )
        return results

    async def _to_results_from_similarity(self, statement: Select) -> list[EmbeddingSearchResult]:
        result = await self._session.execute(statement)
        rows = result.all()
        results: list[EmbeddingSearchResult] = []
        for row in rows:
            results.append(
                EmbeddingSearchResult(
                    allowance=row[0],
                    score=self._clamp_similarity(value=float(row[1])),
                )
            )
        return results

    def _clamp_similarity(self, value: float) -> float:
        return max(-1.0, min(1.0, value))
