import asyncio
import importlib.util
import inspect
import os
import shutil
import socket
import ssl
import time
from abc import ABC, abstractmethod
from urllib.parse import urlparse

from huggingface_hub import __version__ as hf_version
from huggingface_hub import snapshot_download
from packaging import version
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

        if load_timeout_seconds <= 0:
            logger.warning(
                "Non-positive embedding load timeout configured; applying default timeout "
                f"{self._load_timeout_seconds:.1f}s to prevent indefinite startup waits."
            )

        self._log_environment_overrides()

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

            offline_flag = self._parse_env_flag(
                raw_value=os.getenv("HF_HUB_OFFLINE") or os.getenv("TRANSFORMERS_OFFLINE"),
            )
            cache_dir = os.path.join(self._cache_home, "hub")
            await asyncio.to_thread(os.makedirs, cache_dir, 0o777, True)
            self._run_preflight_checks(offline_flag=offline_flag, cache_dir=cache_dir)

            try:
                model_path = await self._download_model_snapshot(
                    offline_flag=offline_flag,
                    cache_dir=cache_dir,
                )
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

            self._validate_model_dimension(model=model)
            self._model = model
            logger.info(
                f"Embedding model '{self._model_name}' loaded successfully with dimension {self._dimension}"
            )
            return model

    def _run_preflight_checks(self, offline_flag: bool, cache_dir: str) -> None:
        """
        Validate environment prerequisites before model download.

        The checks surface common container-specific issues that cause
        downloads to stall indefinitely, such as missing connectivity,
        insufficient disk space, or invalid proxy settings.

        :param offline_flag: Whether offline cache-only mode is requested.
        :param cache_dir: Cache directory for model artifacts.
        :return: None.
        """

        self._verify_huggingface_version()
        self._validate_cache_space(cache_dir=cache_dir)
        self._cleanup_stale_locks(cache_dir=cache_dir)
        self._warn_if_token_missing()
        self._validate_proxy_configuration()
        if not offline_flag:
            self._check_dns_resolution()
            self._check_network_connectivity()
        else:
            logger.info(
                "Offline mode active for embedding download; network checks skipped."
            )

    async def _download_model_snapshot(self, offline_flag: bool, cache_dir: str) -> str:
        """
        Ensure model artifacts are available locally and emit detailed progress logs.

        :return: Filesystem path of the downloaded model snapshot.
        """

        if offline_flag:
            logger.warning(
                f"Offline mode detected while preparing '{self._model_name}'; relying on local cache."
            )

        reporter = _DownloadProgressLogger(model_name=self._model_name)

        logger.info(
            f"Starting snapshot download for '{self._model_name}' to cache '{cache_dir}'."
        )

        if not self._snapshot_supports_progress:
            logger.warning(
                "Installed huggingface_hub does not support progress callbacks; "
                "download progress percentages will be unavailable."
            )

        snapshot_kwargs = self._build_snapshot_kwargs(
            offline_flag=offline_flag,
            cache_dir=cache_dir,
            reporter=reporter,
        )

        hf_transfer_enabled = self._should_use_hf_transfer()
        if self._snapshot_accepts_hf_transfer:
            snapshot_kwargs["use_hf_transfer"] = hf_transfer_enabled
        elif hf_transfer_enabled:
            logger.warning(
                "Fast download using 'hf_transfer' requested but installed huggingface_hub "
                "does not support explicit toggle; relying on environment configuration instead."
            )

        try:
            snapshot_path = await self._run_snapshot_download(snapshot_kwargs)
        except TypeError as exc:
            if "use_hf_transfer" in snapshot_kwargs and "use_hf_transfer" in str(exc):
                logger.warning(
                    "Snapshot download does not accept 'use_hf_transfer'; retrying without explicit toggle."
                )
                snapshot_kwargs.pop("use_hf_transfer", None)
                snapshot_path = await self._run_snapshot_download(snapshot_kwargs)
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

    def _build_snapshot_kwargs(
        self,
        offline_flag: bool,
        cache_dir: str,
        reporter: "_DownloadProgressLogger",
    ) -> dict[str, object]:
        """
        Compose keyword arguments for snapshot download calls.

        :param offline_flag: Indicator for offline cache-only mode.
        :param cache_dir: Destination cache directory.
        :param reporter: Progress logger when supported.
        :return: Dictionary of snapshot_download parameters.
        """

        snapshot_kwargs: dict[str, object] = {
            "repo_id": self._model_name,
            "local_files_only": offline_flag,
            "resume_download": True,
            "cache_dir": cache_dir,
        }

        if self._snapshot_supports_progress:
            snapshot_kwargs["progress_callback"] = reporter

        return snapshot_kwargs

    def _log_environment_overrides(self) -> None:
        """
        Emit diagnostics about environment overrides that affect downloads.

        The goal is to make container misconfiguration visible in logs before
        the model load begins.
        """

        proxy_keys = [
            "http_proxy",
            "https_proxy",
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "ALL_PROXY",
        ]

        for key in proxy_keys:
            if key in os.environ:
                logger.info(f"Environment proxy detected: {key}={os.environ[key]}")

        hf_home = os.getenv("HF_HOME")
        if hf_home:
            logger.info(f"HF_HOME override detected: {hf_home}")

        hf_endpoint = os.getenv("HF_ENDPOINT")
        if hf_endpoint:
            logger.info(f"HF_ENDPOINT override detected: {hf_endpoint}")

        transfer_flag = self._parse_env_flag(os.getenv("HF_HUB_ENABLE_HF_TRANSFER"))
        if transfer_flag:
            logger.info("'hf_transfer' accelerated downloads explicitly enabled via env var")

    def _verify_huggingface_version(self) -> None:
        """
        Ensure the installed huggingface_hub version is recent enough.

        Older versions are prone to hanging downloads; versions older than
        0.22 are rejected with a clear error message.
        """

        current = version.parse(hf_version)
        minimum = version.parse("0.22.0")
        if current < minimum:
            raise RuntimeError(
                "huggingface_hub is too old and may hang during downloads; "
                f"found {hf_version}, require >= {minimum}."
            )

    def _validate_cache_space(self, cache_dir: str) -> None:
        """
        Guard against silent failures when the cache device is full.

        :param cache_dir: Cache directory path.
        :return: None.
        """

        try:
            usage = shutil.disk_usage(cache_dir)
        except OSError as exc:  # noqa: BLE001
            raise RuntimeError(
                f"Unable to determine free space for cache directory '{cache_dir}'."
            ) from exc

        if usage.free < REQUIRED_FREE_SPACE_BYTES:
            raise RuntimeError(
                "Insufficient disk space for embedding model download; "
                f"requires at least {REQUIRED_FREE_SPACE_BYTES / 1024 / 1024 / 1024:.1f}GB free."
            )

    def _cleanup_stale_locks(self, cache_dir: str) -> None:
        """
        Remove stale lock and partial download markers that block new fetches.

        :param cache_dir: Cache directory path.
        :return: None.
        """

        lock_names = ["*.lock", "*.incomplete", "*.tmp"]
        for root_dir, _, files in os.walk(cache_dir):
            for filename in files:
                if any(filename.endswith(pattern[1:]) for pattern in lock_names):
                    full_path = os.path.join(root_dir, filename)
                    try:
                        os.remove(full_path)
                        logger.warning(
                            f"Removed stale download marker blocking model fetch: {full_path}"
                        )
                    except OSError:
                        logger.warning(
                            f"Failed to remove potential stale marker: {full_path}",
                        )

    def _warn_if_token_missing(self) -> None:
        """
        Provide explicit guidance when no Hugging Face token is configured.

        Private or gated models require authentication; surfacing the missing
        token early avoids opaque download hangs.
        """

        if os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN"):
            return

        if "/" in self._model_name:
            logger.warning(
                "No Hugging Face token configured (HF_TOKEN or HUGGINGFACEHUB_API_TOKEN). "
                "Private or gated models will fail to download."
            )

    def _validate_proxy_configuration(self) -> None:
        """
        Detect obvious proxy misconfigurations that can stall HTTPS connections.
        """

        for key in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"):
            raw_value = os.getenv(key)
            if not raw_value:
                continue

            parsed = urlparse(raw_value)
            if not parsed.scheme or not parsed.netloc:
                raise RuntimeError(
                    f"Invalid proxy configuration '{key}={raw_value}'. "
                    "Expected URL with scheme and host."
                )

    def _check_dns_resolution(self) -> None:
        """
        Confirm the Hugging Face host can be resolved inside the container.
        """

        try:
            socket.gethostbyname(SOCKET_PROBE_HOST)
        except socket.gaierror as exc:
            raise RuntimeError(
                f"DNS resolution failed for {SOCKET_PROBE_HOST}; check network or /etc/resolv.conf."
            ) from exc

    def _check_network_connectivity(self) -> None:
        """
        Attempt a short TLS handshake to the Hugging Face endpoint.

        :return: None.
        """

        context = ssl.create_default_context()
        try:
            with socket.create_connection(
                (SOCKET_PROBE_HOST, SOCKET_PROBE_PORT), timeout=SOCKET_PROBE_TIMEOUT
            ) as sock:
                try:
                    with context.wrap_socket(sock, server_hostname=SOCKET_PROBE_HOST):
                        logger.info(
                            f"Connectivity check to {SOCKET_PROBE_HOST}:{SOCKET_PROBE_PORT} succeeded"
                        )
                except ssl.SSLError as exc:  # noqa: BLE001
                    raise RuntimeError(
                        "TLS handshake to huggingface.co failed; check corporate MITM certs or proxy."
                    ) from exc
        except OSError as exc:  # noqa: BLE001
            raise RuntimeError(
                f"Network connection to {SOCKET_PROBE_HOST}:{SOCKET_PROBE_PORT} failed; verify outbound access."
            ) from exc

    async def _run_snapshot_download(self, snapshot_kwargs: dict[str, object]) -> str:
        """
        Execute the snapshot download with the configured timeout applied.

        Applying the same timeout as model initialization ensures startup
        does not hang indefinitely when the Hugging Face servers are
        unreachable.

        :param snapshot_kwargs: Prepared keyword arguments for snapshot_download.
        :return: Path to the downloaded snapshot.
        """

        download_task = asyncio.to_thread(snapshot_download, **snapshot_kwargs)

        if self._load_timeout_seconds > 0:
            try:
                return await asyncio.wait_for(
                    download_task, timeout=self._load_timeout_seconds
                )
            except asyncio.TimeoutError as exc:
                raise RuntimeError(
                    f"Timed out while downloading model files for '{self._model_name}'."
                ) from exc

        return await download_task

    def _should_use_hf_transfer(self) -> bool:
        """
        Decide whether to enable optional hf_transfer acceleration.

        :return: Flag indicating whether hf_transfer can be used safely.
        """

        transfer_flag = self._parse_env_flag(
            raw_value=os.getenv("HF_HUB_ENABLE_HF_TRANSFER"),
        )
        if not transfer_flag:
            return False

        if self._hf_transfer_available():
            return True

        logger.warning(
            "Fast download using 'hf_transfer' requested but package is unavailable; falling back to standard download."
        )
        os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
        return False

    @staticmethod
    def _parse_env_flag(raw_value: str | None) -> bool:
        """
        Convert common truthy environment encodings to boolean form.

        :param raw_value: Raw environment value to interpret.
        :return: Parsed boolean flag.
        """

        if raw_value is None:
            return False

        normalized = raw_value.strip().lower()
        return normalized in {"1", "true", "yes", "on"}

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

    def _validate_model_dimension(self, model: SentenceTransformer) -> None:
        """
        Ensure the configured embedding dimension matches the underlying model.

        This prevents silent schema mismatches with the pgvector column when
        switching to a different embedding model (for example, moving from the
        768-dim E5-base to the 1024-dim multilingual-e5-large-instruct). When no
        dimension is configured (<=0), the model dimension is adopted so API
        clients can proceed after updating the database schema accordingly.
        """

        model_dim = self._determine_model_dimension(model=model)
        if model_dim is None:
            return

        if self._dimension <= 0:
            logger.warning(
                "Embedding dimension not configured or invalid; adopting model dimension %s.",
                model_dim,
            )
            self._dimension = model_dim
            return

        if model_dim != self._dimension:
            raise RuntimeError(
                "Embedding dimension mismatch: configured %s but model '%s' reports %s. "
                "Adjust EMBEDDING_DIM and rerun migrations so the pgvector column matches the model.",
                self._dimension,
                self._model_name,
                model_dim,
            )

    @staticmethod
    def _determine_model_dimension(model: SentenceTransformer) -> int | None:
        """
        Inspect the loaded model to determine its sentence embedding size.

        Returns ``None`` when the information is unavailable so callers can
        skip validation without failing the load sequence.
        """

        getter = getattr(model, "get_sentence_embedding_dimension", None)
        if callable(getter):
            try:
                return int(getter())
            except Exception:  # noqa: BLE001
                return None

        return None


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
