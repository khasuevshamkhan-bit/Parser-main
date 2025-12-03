import asyncio

from sentence_transformers import CrossEncoder

from src.utils.logger import logger


class CrossEncoderReranker:
    """
    Apply cross-encoder scoring to refine initial vector search candidates.
    """

    def __init__(self, model_name: str, load_timeout_seconds: float) -> None:
        self._model_name = model_name
        self._load_timeout_seconds = load_timeout_seconds
        self._model: CrossEncoder | None = None
        self._load_lock = asyncio.Lock()

    @property
    def model_name(self) -> str:
        """
        Return the configured cross-encoder identifier.
        """

        return self._model_name

    async def warm_up(self) -> None:
        """
        Load the cross-encoder model ahead of any search traffic.
        """

        await self._ensure_model_loaded()

    async def score(self, query: str, documents: list[str]) -> list[float]:
        """
        Compute relevance scores for the provided query-document pairs.
        """

        if not documents:
            return []

        model = await self._ensure_model_loaded()
        pairs = [(query, document) for document in documents]
        scores = await asyncio.to_thread(func=model.predict, sentences=pairs)
        return [float(score) for score in scores]

    async def _ensure_model_loaded(self) -> CrossEncoder:
        if self._model:
            return self._model

        async with self._load_lock:
            if self._model:
                return self._model

            logger.info(
                f"Loading cross-encoder '{self._model_name}' with timeout {self._load_timeout_seconds:.1f}s",
            )

            load_task = asyncio.to_thread(func=CrossEncoder, model_name=self._model_name)
            if self._load_timeout_seconds > 0:
                model = await asyncio.wait_for(load_task, timeout=self._load_timeout_seconds)
            else:
                model = await load_task

            self._model = model
            logger.info(
                f"Cross-encoder '{self._model_name}' loaded",
            )
            return model
