import asyncio
from abc import ABC, abstractmethod

from sentence_transformers import SentenceTransformer


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

    def __init__(self, model_name: str, dimension: int) -> None:
        self._model_name = model_name
        self._dimension = dimension
        self._model = SentenceTransformer(model_name)

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed_text(self, text: str) -> list[float]:
        cleaned = text.strip()
        if not cleaned:
            return []

        embedding = await asyncio.to_thread(
            self._model.encode,
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
