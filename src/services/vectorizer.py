import asyncio
from abc import ABC, abstractmethod

from sentence_transformers import SentenceTransformer

from src.utils.logger import logger


DEFAULT_LOAD_TIMEOUT_SECONDS = 300.0


class Vectorizer(ABC):
    """
    Abstract interface for turning text into dense vectors.
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """
        Return the underlying model identifier.
        """

    @property
    @abstractmethod
    def dimension(self) -> int:
        """
        Return the expected embedding dimensionality.
        """

    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        """
        Generate an embedding for the provided text.
        """

    @abstractmethod
    async def warm_up(self) -> None:
        """
        Ensure the underlying model is fully loaded and ready.
        """


class E5Vectorizer(Vectorizer):
    """
    Vectorizer backed by the multilingual E5 model family.
    """

    def __init__(self, model_name: str, dimension: int, load_timeout_seconds: float) -> None:
        self._model_name = model_name
        self._dimension = dimension
        self._load_timeout_seconds = self._resolve_timeout(configured_timeout=load_timeout_seconds)
        self._model: SentenceTransformer | None = None
        self._load_lock = asyncio.Lock()

        if load_timeout_seconds <= 0:
            logger.warning(
                "Non-positive embedding load timeout configured; applying default timeout "
                f"{self._load_timeout_seconds:.1f}s to prevent indefinite startup waits."
            )

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed_text(self, text: str) -> list[float]:
        """
        Generate an embedding for the provided text.

        The text is trimmed before encoding. Returns an empty list when the
        cleaned content is empty.
        """

        cleaned = text.strip()
        if not cleaned:
            return []

        model = await self._ensure_model_loaded()
        embedding = await asyncio.to_thread(
            model.encode,
            cleaned,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        vector = embedding.tolist()

        if len(vector) != self._dimension:
            raise ValueError(
                f"Unexpected embedding size {len(vector)} for model '{self._model_name}', expected {self._dimension}."
            )

        return vector

    async def warm_up(self) -> None:
        """
        Load the embedding model proactively during application startup.
        """

        await self._ensure_model_loaded()

    @staticmethod
    def _resolve_timeout(configured_timeout: float) -> float:
        """
        Determine the timeout used to guard model initialization.

        A non-positive configured timeout is replaced with a safe default to
        avoid unbounded waits when remote model downloads hang.
        """

        if configured_timeout > 0:
            return configured_timeout

        return DEFAULT_LOAD_TIMEOUT_SECONDS

    async def _ensure_model_loaded(self) -> SentenceTransformer:
        """
        Lazily load the embedding model with optional timeout protection.
        """

        if self._model:
            logger.info(f"Embedding model '{self._model_name}' already loaded, reusing instance")
            return self._model

        async with self._load_lock:
            if self._model:
                logger.info(f"Embedding model '{self._model_name}' already loaded, reusing instance")
                return self._model

            timeout = self._load_timeout_seconds
            logger.info(
                f"Loading embedding model '{self._model_name}' with timeout {timeout:.1f}s"
            )

            progress_stop = asyncio.Event()
            progress_task: asyncio.Task | None = None

            async def _log_progress() -> None:
                loop = asyncio.get_running_loop()
                started = loop.time()
                while not progress_stop.is_set():
                    await asyncio.sleep(15)
                    elapsed = loop.time() - started
                    if not progress_stop.is_set():
                        logger.info(
                            f"Embedding model '{self._model_name}' still loading (elapsed {elapsed:.1f}s)"
                        )

            try:
                progress_task = asyncio.create_task(_log_progress())
                if timeout and timeout > 0:
                    model = await asyncio.wait_for(
                        asyncio.to_thread(SentenceTransformer, self._model_name),
                        timeout=timeout,
                    )
                else:
                    model = await asyncio.to_thread(
                        SentenceTransformer,
                        self._model_name,
                    )
            except asyncio.TimeoutError as exc:
                raise RuntimeError(
                    f"Timed out while loading embedding model '{self._model_name}'."
                ) from exc
            except Exception as exc:  # noqa: BLE001
                raise RuntimeError(
                    f"Failed to load embedding model '{self._model_name}'."
                ) from exc
            finally:
                progress_stop.set()
                if progress_task:
                    await progress_task

            self._model = model
            logger.info(f"Embedding model '{self._model_name}' loaded successfully")
            return model
