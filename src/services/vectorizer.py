import asyncio
import inspect
import os
import time
from abc import ABC, abstractmethod

from huggingface_hub import snapshot_download
from huggingface_hub.constants import HF_HUB_CACHE
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

            logger.info(
                f"Preparing model files for '{self._model_name}' using cache directory '{HF_HUB_CACHE}'."
            )

            try:
                model_path = await self._download_model_snapshot()
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    f"Failed to download model files for '{self._model_name}' before initialization."
                )
                raise RuntimeError(
                    f"Failed to download model files for '{self._model_name}'."
                ) from exc

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
                        asyncio.to_thread(SentenceTransformer, model_path),
                        timeout=timeout,
                    )
                else:
                    model = await asyncio.to_thread(
                        SentenceTransformer,
                        model_path,
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

    async def _download_model_snapshot(self) -> str:
        """
        Ensure model artifacts are available locally and emit detailed progress logs.
        """

        offline_flag = os.getenv("HF_HUB_OFFLINE") or os.getenv("TRANSFORMERS_OFFLINE")
        if offline_flag:
            logger.warning(
                f"Offline mode detected while preparing '{self._model_name}'; relying on local cache."
            )

        reporter = _DownloadProgressLogger(model_name=self._model_name)

        supports_progress = "progress_callback" in inspect.signature(snapshot_download).parameters

        logger.info(
            f"Starting snapshot download for '{self._model_name}' to cache '{HF_HUB_CACHE}'."
        )

        if not supports_progress:
            logger.warning(
                "Installed huggingface_hub does not support progress callbacks; "
                "download progress percentages will be unavailable."
            )

        snapshot_kwargs = {
            "repo_id": self._model_name,
            "local_files_only": bool(offline_flag),
            "resume_download": True,
        }

        if supports_progress:
            snapshot_kwargs["progress_callback"] = reporter

        try:
            snapshot_path = await asyncio.to_thread(
                snapshot_download,
                **snapshot_kwargs,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                f"Snapshot download failed for '{self._model_name}' with error: {exc}"
            )
            raise

        reporter.log_final()
        logger.info(
            f"Snapshot for '{self._model_name}' available at '{snapshot_path}'."
        )

        return snapshot_path


class _DownloadProgressLogger:
    """
    Helper to log download progress with percentages and throughput.
    """

    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._start_time = time.monotonic()
        self._last_logged_time = self._start_time
        self._last_logged_bytes = 0
        self._last_logged_percent = -1.0
        self._total_bytes: int | None = None

    def __call__(self, current_bytes: int, total_bytes: int) -> None:
        self._total_bytes = total_bytes if total_bytes > 0 else None
        now = time.monotonic()
        elapsed_since_last = now - self._last_logged_time

        percent = self._calculate_percent(current_bytes=current_bytes)
        if not self._should_log(percent=percent, elapsed_since_last=elapsed_since_last):
            return

        speed = self._calculate_speed(
            current_bytes=current_bytes,
            elapsed_since_last=elapsed_since_last,
        )
        total_mb = self._bytes_to_megabytes(self._total_bytes)
        current_mb = self._bytes_to_megabytes(current_bytes)

        if total_mb is not None:
            logger.info(
                f"Downloading '{self._model_name}': {current_mb:.1f}MB / {total_mb:.1f}MB "
                f"({percent:.1f}%) at {speed:.2f}MB/s"
            )
        else:
            logger.info(
                f"Downloading '{self._model_name}': {current_mb:.1f}MB downloaded, total size unknown "
                f"at {speed:.2f}MB/s"
            )

        self._last_logged_time = now
        self._last_logged_bytes = current_bytes
        self._last_logged_percent = percent

    def log_final(self) -> None:
        if self._total_bytes is None:
            return

        total_mb = self._bytes_to_megabytes(self._total_bytes)
        elapsed = time.monotonic() - self._start_time
        avg_speed = (self._total_bytes / 1024 / 1024) / elapsed if elapsed > 0 else 0.0
        logger.info(
            f"Completed download for '{self._model_name}': {total_mb:.1f}MB in {elapsed:.1f}s "
            f"(avg {avg_speed:.2f}MB/s)"
        )

    def _calculate_percent(self, current_bytes: int) -> float:
        if not self._total_bytes:
            return 0.0

        return (current_bytes / self._total_bytes) * 100

    def _should_log(self, percent: float, elapsed_since_last: float) -> bool:
        if elapsed_since_last < 1.0 and percent - self._last_logged_percent < 5.0:
            return False

        return True

    def _calculate_speed(self, current_bytes: int, elapsed_since_last: float) -> float:
        delta_bytes = current_bytes - self._last_logged_bytes
        if elapsed_since_last <= 0:
            return 0.0

        return (delta_bytes / 1024 / 1024) / elapsed_since_last

    def _bytes_to_megabytes(self, size_in_bytes: int | None) -> float | None:
        if size_in_bytes is None:
            return None

        return size_in_bytes / 1024 / 1024
