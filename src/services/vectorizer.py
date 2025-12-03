import asyncio
import hashlib
import os
from abc import ABC, abstractmethod

import numpy as np
from sentence_transformers import SentenceTransformer

from src.utils.logger import logger

DEFAULT_LOAD_TIMEOUT_SECONDS = 300.0
REQUIRED_FREE_SPACE_BYTES = 2_000_000_000  # ~2GB safeguard for model artifacts
SOCKET_PROBE_HOST = "huggingface.co"
SOCKET_PROBE_PORT = 443
SOCKET_PROBE_TIMEOUT = 5


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


class HashVectorizer(Vectorizer):
    """
    Offline-friendly deterministic vectorizer using hashing.

    This backend avoids any network downloads by deriving fixed-size vectors from
    the input text via a seeded NumPy RNG. It is intended for local development
    and CI environments where Hugging Face access is blocked.
    """

    def __init__(self, dimension: int = 384) -> None:
        self._dimension = max(8, dimension)  # keep a reasonable minimum

    @property
    def model_name(self) -> str:
        return "local-hash"

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed_text(self, text: str) -> list[float]:
        cleaned = text.strip()
        if not cleaned:
            return []

        seed_bytes = hashlib.sha256(cleaned.encode("utf-8")).digest()
        seed = int.from_bytes(seed_bytes[:8], "little", signed=False)
        vector = await asyncio.to_thread(func=self._generate_vector, seed=seed)
        return vector

    def _generate_vector(self, seed: int) -> list[float]:
        rng = np.random.default_rng(seed)
        raw = rng.standard_normal(self._dimension)
        norm = np.linalg.norm(raw)
        if norm == 0:
            return [0.0] * self._dimension
        normalized = raw / norm
        return normalized.tolist()

    async def warm_up(self) -> None:
        # Nothing to preload for the hash backend
        return


class E5Vectorizer(Vectorizer):
    """
    Vectorizer backed by the multilingual E5 model family.

    The E5 family expects every query to be prefixed with ``"query: "`` and
    every document with ``"passage: "`` (even for Russian text). Builders keep
    that contract so callers only need to pass in raw questionnaire or allowance
    text.
    """

    def __init__(
            self,
            model_name: str,
            dimension: int,
            load_timeout_seconds: float,
            offline: bool,
            local_model_path: str | None = None,
    ) -> None:
        self._model_name = model_name
        self._configured_dimension = dimension
        self._load_timeout_seconds = load_timeout_seconds if load_timeout_seconds > 0 else DEFAULT_LOAD_TIMEOUT_SECONDS
        self._model: SentenceTransformer | None = None
        self._load_lock = asyncio.Lock()
        self._cache_dir = self._resolve_cache_dir()
        self._offline = offline
        self._local_model_path = local_model_path

        logger.info(
            f"Embedding model configured",
            f"model: {self._model_name}",
            f"dimension: {self._configured_dimension}",
            f"cache_dir: {self._cache_dir}",
            f"offline: {self._offline}",
            f"local_model_path: {self._local_model_path}",
            f"timeout_seconds: {self._load_timeout_seconds}",
        )

        if load_timeout_seconds <= 0:
            logger.warning(
                "Non-positive embedding load timeout configured; applying default timeout "
                f"{self._load_timeout_seconds:.1f}s."
            )

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._configured_dimension

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
        vector = await asyncio.to_thread(
            func=model.encode,
            sentences=cleaned,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )

        values = self._normalize_vector(raw_vector=vector)
        if len(values) != self._configured_dimension:
            raise ValueError(
                "Unexpected embedding size for model '{model}': got {got}, expected {expected}. "
                "Set EMBEDDING_DIM to the model's dimension and re-run the pgvector migration."
                .format(
                    model=self._model_name,
                    got=len(values),
                    expected=self._configured_dimension,
                )
            )

        return values

    async def warm_up(self) -> None:
        """
        Load the embedding model proactively during application startup.
        """

        await self._ensure_model_loaded()

    async def _ensure_model_loaded(self) -> SentenceTransformer:
        if self._model:
            return self._model

        async with self._load_lock:
            if self._model:
                return self._model

            logger.info(
                f"Loading embedding model '{self._model_name}' (offline={self._offline})"
            )

            load_task = asyncio.to_thread(
                func=self._load_model,
            )

            if self._load_timeout_seconds > 0:
                model = await asyncio.wait_for(load_task, timeout=self._load_timeout_seconds)
            else:
                model = await load_task

            self._validate_dimension(model)
            self._model = model
            logger.info(
                f"Embedding model '{self._model_name}' loaded with dimension {self._configured_dimension}"
            )
            return model

    def _load_model(self) -> SentenceTransformer:
        model_source = self._local_model_path or self._model_name
        if self._offline:
            if self._local_model_path:
                if not os.path.exists(self._local_model_path):
                    raise RuntimeError(
                        f"Offline mode is enabled but local model path '{self._local_model_path}' does not exist. "
                        "Mount or bake the model files into the image and set EMBEDDING_LOCAL_MODEL to that path."
                    )
            else:
                candidate_dir = os.path.join(self._cache_dir, "models", self._sanitize_model_name())
                if not os.path.isdir(candidate_dir):
                    raise RuntimeError(
                        "Offline mode is enabled; no local model files were found. "
                        "Download the model once and mount it to EMBEDDING_LOCAL_MODEL or to the Hugging Face cache."
                    )
                model_source = candidate_dir

        return SentenceTransformer(
            model_source,
            cache_folder=self._cache_dir,
            local_files_only=self._offline,
        )

    def _validate_dimension(self, model: SentenceTransformer) -> None:
        actual_dim = model.get_sentence_embedding_dimension()
        if self._configured_dimension == actual_dim:
            return

        if self._configured_dimension <= 0:
            logger.warning(
                "EMBEDDING_DIM was non-positive; adopting model dimension %s", actual_dim
            )
            self._configured_dimension = actual_dim
            return

        raise RuntimeError(
            "Model dimension mismatch: configured %s, model reports %s. "
            "Update EMBEDDING_DIM and the pgvector column dimension to proceed." % (
                self._configured_dimension,
                actual_dim,
            )
        )

    def _resolve_cache_dir(self) -> str:
        explicit = os.getenv("HF_HOME")
        default_home = os.path.join(os.path.expanduser("~"), ".cache", "huggingface")
        for candidate in [explicit, default_home, "/tmp/huggingface"]:
            if not candidate:
                continue
            try:
                os.makedirs(candidate, exist_ok=True)
                test_file = os.path.join(candidate, ".write_test")
                with open(test_file, "w", encoding="utf-8") as handle:
                    handle.write("ok")
                os.remove(test_file)
                return candidate
            except OSError:
                logger.warning("Cache directory '%s' is not writable; trying fallback", candidate)
        raise RuntimeError("No writable Hugging Face cache directory available.")

    def _sanitize_model_name(self) -> str:
        return self._model_name.replace("/", "__")

    def _normalize_vector(self, raw_vector: list[float] | np.ndarray) -> list[float]:
        array = np.asarray(a=raw_vector, dtype=np.float64)
        norm = np.linalg.norm(x=array)
        if norm == 0:
            return [0.0] * len(array)
        normalized = array / norm
        return normalized.tolist()


def create_vectorizer(
        backend: str,
        model_name: str,
        dimension: int,
        load_timeout_seconds: float,
        offline: bool,
        local_model_path: str | None = None,
) -> Vectorizer:
    normalized_backend = (backend or "").strip().lower()
    if normalized_backend == "hash":
        logger.info(
            "Using offline hash vectorizer backend"
        )
        return HashVectorizer(dimension=dimension)

    if normalized_backend in {"hf", "huggingface", "e5"}:
        return E5Vectorizer(
            model_name=model_name,
            dimension=dimension,
            load_timeout_seconds=load_timeout_seconds,
            offline=offline,
            local_model_path=local_model_path,
        )

    raise ValueError(
        f"Unsupported EMBEDDING_BACKEND '{backend}'. Use 'hash' for offline hash embeddings or 'hf' for Hugging Face models."
    )
