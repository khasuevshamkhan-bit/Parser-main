import asyncio
import random
from abc import ABC, abstractmethod
from enum import Enum

import httpx

from src.models.dto.allowances import AllowanceDTO
from src.utils.logger import logger


class UserAgent(str, Enum):
    """
    User agent options for outgoing HTTP requests.
    """

    CHROME_WINDOWS = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    SAFARI_MAC = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15"
    CHROME_LINUX = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"


class BaseParser(ABC):
    """
    Base asynchronous parser with rate limiting and user agent rotation.

    Provides common infrastructure for web scraping including
    concurrency control, random delays, and HTTP client management.
    """

    min_delay_seconds: float = 0.5
    max_delay_seconds: float = 2.5
    concurrency_limit: int = 4
    user_agents: tuple[UserAgent, ...] = (
        UserAgent.CHROME_WINDOWS,
        UserAgent.SAFARI_MAC,
        UserAgent.CHROME_LINUX,
    )

    def __init__(self) -> None:
        self._semaphore = asyncio.Semaphore(self.concurrency_limit)
        self._parser_name = self.__class__.__name__

    async def run(self) -> list[AllowanceDTO]:
        """
        Execute the parsing lifecycle and return normalized allowances.

        :return: list of parsed allowances
        """

        logger.info(f"[{self._parser_name}] Starting parsing process")

        try:
            sources = await self.fetch_sources()
            logger.info(f"[{self._parser_name}] Discovered {len(sources)} sources to parse")

            if not sources:
                logger.warning(f"[{self._parser_name}] No sources found, returning empty list")
                return []

            for idx, source in enumerate(sources, start=1):
                logger.debug(f"[{self._parser_name}] Source {idx}: {source}")

            tasks = [self._bounded_parse(source=source) for source in sources]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            allowances: list[AllowanceDTO] = []
            successful_count = 0
            failed_count = 0

            for idx, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_count += 1
                    logger.error(
                        f"[{self._parser_name}] Failed to parse source {idx + 1}: {result}"
                    )
                else:
                    successful_count += 1
                    allowances.extend(result)

            logger.info(
                f"[{self._parser_name}] Parsing completed: "
                f"{successful_count} sources succeeded, {failed_count} failed, "
                f"{len(allowances)} allowances extracted"
            )

            return allowances

        except Exception as e:
            logger.error(f"[{self._parser_name}] Critical error during parsing: {e}")
            raise

    async def _bounded_parse(self, source: str) -> list[AllowanceDTO]:
        """
        Parse a single source URL within concurrency bounds.

        :param source: URL to parse
        :return: allowances found in the source
        """

        async with self._semaphore:
            delay = await self._random_delay()
            logger.debug(f"[{self._parser_name}] Parsing {source} (delayed {delay:.2f}s)")

            try:
                result = await self.parse_source(source=source)
                logger.debug(
                    f"[{self._parser_name}] Extracted {len(result)} allowances from {source}"
                )
                return result
            except Exception as e:
                logger.error(f"[{self._parser_name}] Error parsing {source}: {e}")
                raise

    async def _random_delay(self) -> float:
        """
        Sleep for a random duration to reduce request bursts.

        :return: actual delay duration in seconds
        """

        delay = random.uniform(self.min_delay_seconds, self.max_delay_seconds)
        await asyncio.sleep(delay)
        return delay

    def _create_client(self) -> httpx.AsyncClient:
        """
        Build an HTTP client with browser-like headers.

        :return: configured asynchronous HTTP client
        """

        agent = random.choice(self.user_agents)
        headers = {
            "User-Agent": agent.value,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
        }
        logger.debug(f"[{self._parser_name}] Created HTTP client with agent: {agent.name}")
        return httpx.AsyncClient(headers=headers, timeout=20.0, follow_redirects=True)

    @abstractmethod
    async def fetch_sources(self) -> list[str]:
        """
        Discover source URLs to parse.

        :return: list of URLs for parsing
        """

    @abstractmethod
    async def parse_source(self, source: str) -> list[AllowanceDTO]:
        """
        Parse allowance data from a source URL.

        :param source: URL to parse
        :return: parsed allowances from the source
        """
