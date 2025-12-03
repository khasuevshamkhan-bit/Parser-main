import asyncio
import importlib.util
import inspect
import os
import time
from abc import ABC, abstractmethod

from huggingface_hub import snapshot_download
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

        :return: Model identifier.
        """

    @property
    @abstractmethod
    def dimension(self) -> int:
        """
        Return the expected embedding dimensionality.

        :return: Embedding dimensionality.
        """

    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        """
        Generate an embedding for the provided text.

        :param text: Source text to encode.
        :return: Normalized embedding vector.
        """

    @abstractmethod
    async def warm_up(self) -> None:
        """
        Ensure the underlying model is fully loaded and ready.

        :return: None.
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
        self._cache_home = self._resolve_cache_home()
        signature = inspect.signature(snapshot_download)
        self._snapshot_supports_progress = "progress_callback" in signature.parameters
        self._snapshot_accepts_hf_transfer = "use_hf_transfer" in signature.parameters

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

        :param text: Source text to encode.
        :return: Normalized embedding vector.
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

        :return: None.
        """

        await self._ensure_model_loaded()

    @staticmethod
    def _resolve_timeout(configured_timeout: float) -> float:
        """
        Determine the timeout used to guard model initialization.

        A non-positive configured timeout is replaced with a safe default to
        avoid unbounded waits when remote model downloads hang.

        :param configured_timeout: Timeout requested by configuration.
        :return: Timeout used for model initialization.
        """

        if configured_timeout > 0:
            return configured_timeout

        return DEFAULT_LOAD_TIMEOUT_SECONDS

    async def _ensure_model_loaded(self) -> SentenceTransformer:
        """
        Lazily load the embedding model with optional timeout protection.

        :return: Loaded embedding model.
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
                f"Preparing model files for '{self._model_name}' using cache directory '{self._cache_home}'."
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

        :return: Filesystem path of the downloaded model snapshot.
        """

        offline_flag = os.getenv("HF_HUB_OFFLINE") or os.getenv("TRANSFORMERS_OFFLINE")
        if offline_flag:
            logger.warning(
                f"Offline mode detected while preparing '{self._model_name}'; relying on local cache."
            )

        reporter = _DownloadProgressLogger(model_name=self._model_name)
        cache_dir = os.path.join(self._cache_home, "hub")
        os.makedirs(cache_dir, exist_ok=True)

        logger.info(
            f"Starting snapshot download for '{self._model_name}' to cache '{cache_dir}'."
        )

        if not self._snapshot_supports_progress:
            logger.warning(
                "Installed huggingface_hub does not support progress callbacks; "
                "download progress percentages will be unavailable."
            )

        snapshot_kwargs = {
            "repo_id": self._model_name,
            "local_files_only": bool(offline_flag),
            "resume_download": True,
            "cache_dir": cache_dir,
            "use_hf_transfer": use_hf_transfer,
        }

        hf_transfer_enabled = self._should_use_hf_transfer()
        if self._snapshot_accepts_hf_transfer:
            snapshot_kwargs["use_hf_transfer"] = hf_transfer_enabled
        elif hf_transfer_enabled:
            logger.warning(
                "Fast download using 'hf_transfer' requested but installed huggingface_hub "
                "does not support explicit toggle; relying on environment configuration instead."
            )

        if self._snapshot_supports_progress:
            snapshot_kwargs["progress_callback"] = reporter

        try:
            snapshot_path = await asyncio.to_thread(
                snapshot_download,
                **snapshot_kwargs,
            )
        except TypeError as exc:
            if "use_hf_transfer" in snapshot_kwargs and "use_hf_transfer" in str(exc):
                logger.warning(
                    "Snapshot download does not accept 'use_hf_transfer'; retrying without explicit toggle."
                )
                snapshot_kwargs.pop("use_hf_transfer", None)
                snapshot_path = await asyncio.to_thread(
                    snapshot_download,
                    **snapshot_kwargs,
                )
            else:
                logger.error(
                    f"Snapshot download failed for '{self._model_name}' with error: {exc}"
                )
                raise
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

    def _should_use_hf_transfer(self) -> bool:
        """
        Decide whether to enable optional hf_transfer acceleration.

        :return: Flag indicating whether hf_transfer can be used safely.
        """

        transfer_flag = os.getenv("HF_HUB_ENABLE_HF_TRANSFER")
        if not transfer_flag or transfer_flag in {"0", "false", "False"}:
            return False

        if self._hf_transfer_available():
            return True

        logger.warning(
            "Fast download using 'hf_transfer' requested but package is unavailable; falling back to standard download."
        )
        os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
        return False

    @staticmethod
    def _hf_transfer_available() -> bool:
        """
        Determine whether the hf_transfer package can be imported.

        :return: Flag indicating availability of hf_transfer.
        """

        return importlib.util.find_spec("hf_transfer") is not None

    def _resolve_cache_home(self) -> str:
        """
        Resolve a writable Hugging Face cache directory with a safe fallback.

        Preference is given to the HF_HOME environment variable. When the
        configured path is not writable, the directory is redirected to
        ``/tmp/huggingface`` to avoid permission failures on startup.

        :return: Path to the resolved cache directory.
        """

        configured_home = os.getenv("HF_HOME") or os.path.join(
            os.path.expanduser("~"),
            ".cache",
            "huggingface",
        )
        candidates = [configured_home, "/tmp/huggingface"]

        for path in candidates:
            try:
                os.makedirs(path, exist_ok=True)
                test_path = os.path.join(path, ".write_test")
                with open(test_path, "w", encoding="utf-8") as handle:
                    handle.write("ok")
                os.remove(test_path)
                os.environ["HF_HOME"] = path
                return path
            except OSError:
                logger.warning(
                    f"Cache directory '{path}' is not writable; attempting fallback.",
                )

        raise RuntimeError("No writable Hugging Face cache directory available.")


class _DownloadProgressLogger:
    """
    Helper to log download progress with percentages and throughput.

    :param model_name: Identifier of the model being downloaded.
    """

    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._start_time = time.monotonic()
        self._last_logged_time = self._start_time
        self._last_logged_bytes = 0
        self._last_logged_percent = -1.0
        self._total_bytes: int | None = None

    def __call__(self, current_bytes: int, total_bytes: int) -> None:
        """
        Emit progress metrics for the current download state.

        :param current_bytes: Number of bytes downloaded so far.
        :param total_bytes: Total payload size if known.
        """

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
        """
        Log completion metrics once the download finishes.

        :return: None.
        """

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
        """
        Convert the current byte offset into a percentage.

        :param current_bytes: Number of bytes downloaded so far.
        :return: Download completion percentage.
        """

        if not self._total_bytes:
            return 0.0

        return (current_bytes / self._total_bytes) * 100

    def _should_log(self, percent: float, elapsed_since_last: float) -> bool:
        """
        Determine whether the current progress event should be emitted.

        :param percent: Percentage completed.
        :param elapsed_since_last: Seconds since the last emitted message.
        :return: Flag indicating whether to emit the log entry.
        """

        if elapsed_since_last < 1.0 and percent - self._last_logged_percent < 5.0:
            return False

        return True

    def _calculate_speed(self, current_bytes: int, elapsed_since_last: float) -> float:
        """
        Compute instantaneous download speed in megabytes per second.

        :param current_bytes: Number of bytes downloaded so far.
        :param elapsed_since_last: Seconds since the prior event.
        :return: Instantaneous download speed in megabytes per second.
        """

        delta_bytes = current_bytes - self._last_logged_bytes
        if elapsed_since_last <= 0:
            return 0.0

        return (delta_bytes / 1024 / 1024) / elapsed_since_last

    def _bytes_to_megabytes(self, size_in_bytes: int | None) -> float | None:
        """
        Convert byte counts to megabytes.

        :param size_in_bytes: Byte count to convert.
        :return: Size converted to megabytes when available.
        """

        if size_in_bytes is None:
            return None

        return size_in_bytes / 1024 / 1024
