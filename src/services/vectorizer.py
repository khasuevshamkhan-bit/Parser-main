import asyncio
from abc import ABC, abstractmethod

from sentence_transformers import SentenceTransformer

from src.utils.logger import logger


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


class E5Vectorizer(Vectorizer):
    """
    Vectorizer backed by the multilingual E5 model family.
    """

    def __init__(self, model_name: str, dimension: int, load_timeout_seconds: float) -> None:
        self._model_name = model_name
        self._dimension = dimension
        self._load_timeout_seconds = load_timeout_seconds
        self._model: SentenceTransformer | None = None
        self._load_lock = asyncio.Lock()

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed_text(self, text: str) -> list[float]:
        """
        Generate an embedding for the provided text.

        :param text: raw text to encode into a dense vector
        :return: embedding vector with the configured dimensionality
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

    async def _ensure_model_loaded(self) -> SentenceTransformer:
        """
        Lazily load the embedding model with timeout protection.

        :return: initialized sentence transformer model
        """

        if self._model:
            return self._model

        async with self._load_lock:
            if self._model:
                return self._model

            logger.info(
                message=(
                    f"Loading embedding model '{self._model_name}' "
                    f"with timeout {self._load_timeout_seconds:.1f}s"
                )
            )

            try:
                model = await asyncio.wait_for(
                    asyncio.to_thread(SentenceTransformer, self._model_name),
                    timeout=self._load_timeout_seconds,
                )
            except asyncio.TimeoutError as exc:
                raise RuntimeError(
                    f"Timed out while loading embedding model '{self._model_name}'."
                ) from exc
            except Exception as exc:  # noqa: BLE001
                raise RuntimeError(
                    f"Failed to load embedding model '{self._model_name}'."
                ) from exc

            self._model = model
            logger.info(
                message=f"Embedding model '{self._model_name}' loaded successfully"
            )
            return model
