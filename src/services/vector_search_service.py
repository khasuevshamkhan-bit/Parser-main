from difflib import SequenceMatcher

from src.models.dto.search import SearchResultDTO
from src.repositories.allowance_repository import AllowanceRepository


class VectorSearchService:
    """
    Service for performing vector-like searches over allowances.

    Uses a lightweight similarity heuristic to order allowances by relevance.
    """

    def __init__(self, repository: AllowanceRepository) -> None:
        self._repository = repository

    async def search(self, query: str, limit: int = 5) -> list[SearchResultDTO]:
        """
        Run a similarity search over stored allowances.

        :param query: free-form query string
        :param limit: maximum number of results to return
        :return: ordered list of search results
        """

        cleaned_query = query.strip()
        if not cleaned_query:
            return []

        allowances = await self._repository.list_all()

        scored: list[SearchResultDTO] = []
        for allowance in allowances:
            haystack = " ".join(filter(None, [allowance.name, allowance.npa_name]))
            similarity = SequenceMatcher(
                None, cleaned_query.lower(), haystack.lower()
            ).ratio()
            scored.append(
                SearchResultDTO(id=allowance.id, name=allowance.name, score=similarity)
            )

        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:limit]
