from src.config import settings
from src.models.dto.vector_search import VectorSearchResultDTO
from src.repositories.allowance_embedding_repository import (
    AllowanceEmbeddingRepository,
    EmbeddingSearchResult,
)
from src.services.allowance_embedding_service import AllowanceEmbeddingService
from src.services.embedding_builder import AllowanceEmbeddingBuilder, QueryEmbeddingBuilder, TextNormalizer
from src.services.reranker import CrossEncoderReranker
from src.services.vectorizer import Vectorizer


class VectorSearchService:
    """
    Execute semantic search over allowance embeddings and reranking pipelines.

    The service wraps vector preparation, repository querying, score filtering,
    and optional cross-encoder reranking to provide consistent and transparent
    search results for allowances.
    """

    def __init__(
            self,
            embedding_repository: AllowanceEmbeddingRepository,
            vectorizer: Vectorizer,
            query_builder: QueryEmbeddingBuilder,
            embedding_service: AllowanceEmbeddingService,
            document_builder: AllowanceEmbeddingBuilder,
            reranker: CrossEncoderReranker | None,
    ) -> None:
        self._embedding_repository = embedding_repository
        self._vectorizer = vectorizer
        self._query_builder = query_builder
        self._embedding_service = embedding_service
        self._document_builder = document_builder
        self._reranker = reranker
        self._default_limit = settings.vector.search_limit
        self._score_threshold = settings.vector.min_score_threshold
        self._search_metric = settings.vector.search_metric
        self._rerank_candidates = max(settings.vector.rerank_candidates, self._default_limit)
        self._rerank_top_k = max(1, settings.vector.rerank_top_k)
        self._rerank_enabled = settings.vector.enable_rerank and reranker is not None
        self._text_normalizer = TextNormalizer()

    @property
    def default_limit(self) -> int:
        """
        Return the configured default search limit.

        :return: default number of results returned when no limit is provided.
        """

        return self._default_limit

    async def search(
            self,
            query_text: str,
            limit: int | None = None
    ) -> list[VectorSearchResultDTO]:
        """
        Perform a vector similarity search using questionnaire text.

        The method indexes any missing embeddings, normalizes and formats the
        query, embeds it with the configured vectorizer, and queries the
        repository using the configured similarity metric. Results below the
        configured score threshold are removed, the remainder is optionally
        reranked with a cross-encoder, and the final list is sorted in
        descending score order.

        :param query_text: questionnaire text provided by the user.
        :param limit: optional cap on returned matches; defaults to the service
            configuration when not provided.
        :return: ordered list of allowance matches suitable for API responses.
        """

        await self._embedding_service.index_missing()

        normalized_query = self._query_builder.build_query(user_input=query_text)
        if not normalized_query:
            return []

        vector = await self._vectorizer.embed_text(text=normalized_query)
        if not vector:
            return []

        requested_limit = limit or self._default_limit
        search_limit = max(requested_limit, self._rerank_candidates)
        matches = await self._embedding_repository.search_by_vector(
            embedding=vector,
            limit=search_limit,
            metric=self._search_metric,
        )
        filtered_matches = self._filter_by_score(matches=matches)
        if not filtered_matches:
            return []

        reranked = await self._rerank(
            user_query=query_text,
            candidates=filtered_matches,
            limit=requested_limit,
        )

        results = [self._to_dto(match=match) for match in reranked]
        return self._sorted_by_score(results=results)

    @staticmethod
    def _to_dto(match: EmbeddingSearchResult) -> VectorSearchResultDTO:
        """
        Convert a repository match into an API response object.

        :param match: embedding search result containing allowance metadata and
            similarity score.
        :return: DTO carrying allowance identifiers, names, and scores.
        """

        return VectorSearchResultDTO(
            allowance_id=match.allowance.id,
            allowance_name=match.allowance.name,
            score=match.score,
        )

    def _filter_by_score(self, matches: list[EmbeddingSearchResult]) -> list[EmbeddingSearchResult]:
        """
        Remove matches below the configured similarity threshold.

        :param matches: raw search results returned by the repository.
        :return: subset of results that meet or exceed the score threshold.
        """

        if self._score_threshold <= 0:
            return matches
        return [match for match in matches if match.score >= self._score_threshold]

    async def _rerank(
            self,
            user_query: str,
            candidates: list[EmbeddingSearchResult],
            limit: int,
    ) -> list[EmbeddingSearchResult]:
        """
        Refine the top candidates using a cross-encoder when available.

        :param user_query: original user input used for reranking context.
        :param candidates: filtered matches eligible for reranking.
        :param limit: maximum number of matches to return after reranking.
        :return: reranked and truncated list of matches.
        """

        if not self._rerank_enabled or not candidates:
            return self._truncate_sorted(matches=candidates, limit=limit)

        query_for_rerank = self._text_normalizer.normalize(value=user_query)
        if not query_for_rerank:
            return self._truncate_sorted(matches=candidates, limit=limit)

        rerank_limit = min(limit, self._rerank_top_k)
        pool = candidates[:max(self._rerank_candidates, rerank_limit)]
        documents = self._build_documents(matches=pool)
        if not documents:
            return self._truncate_sorted(matches=candidates, limit=limit)

        scores = await self._reranker.score(query=query_for_rerank, documents=documents)
        scored = [
            EmbeddingSearchResult(
                allowance=match.allowance,
                score=score,
            )
            for match, score in zip(pool, scores, strict=False)
        ]
        if not scored:
            return self._truncate_sorted(matches=candidates, limit=limit)

        return self._truncate_sorted(matches=scored, limit=rerank_limit)

    def _build_documents(self, matches: list[EmbeddingSearchResult]) -> list[str]:
        """
        Build passage-rich documents for reranking input.

        :param matches: matches selected for reranking.
        :return: textual representations combining allowance fields.
        """
        documents: list[str] = []
        for match in matches:
            document = self._document_builder.build_document(
                name=match.allowance.name,
                npa_name=match.allowance.npa_name,
                level=match.allowance.level,
                subjects=match.allowance.subjects,
                validity_period=match.allowance.validity_period,
            )
            if document:
                documents.append(document)
        return documents

    def _truncate_sorted(self, matches: list[EmbeddingSearchResult], limit: int) -> list[EmbeddingSearchResult]:
        """
        Sort matches by score and apply a hard limit.

        :param matches: search results to order and trim.
        :param limit: maximum number of matches to return.
        :return: top matches ordered by descending score.
        """
        sorted_matches = sorted(matches, key=lambda item: item.score, reverse=True)
        return sorted_matches[:limit]

    @staticmethod
    def _sorted_by_score(results: list[VectorSearchResultDTO]) -> list[VectorSearchResultDTO]:
        """
        Sort DTO results by score in descending order.

        :param results: search result DTOs.
        :return: ordered DTOs with highest scores first.
        """
        return sorted(results, key=lambda item: item.score, reverse=True)
