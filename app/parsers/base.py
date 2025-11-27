import asyncio
import random
from abc import ABC, abstractmethod
from enum import Enum

import httpx

from app.dto import AllowanceDTO


class UserAgent(str, Enum):
    """
    User agent options for outgoing HTTP requests.

    :return: enumeration of user agents
    """

    CHROME_WINDOWS = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    SAFARI_MAC = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15"
    CHROME_LINUX = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"


class BaseParser(ABC):
    """
    Base asynchronous parser with rate limiting and user agent rotation.

    :return: initialized parser instance
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

    async def run(self) -> list[AllowanceDTO]:
        """
        Execute the parsing lifecycle and return normalized allowances.

        :return: list of parsed allowances
        """

        sources = await self.fetch_sources()
        tasks = [self._bounded_parse(source) for source in sources]
        results = await asyncio.gather(*tasks)
        allowances = []
        for batch in results:
            allowances.extend(batch)
        return allowances

    async def _bounded_parse(self, source: str) -> list[AllowanceDTO]:
        """
        Parse a single source URL within concurrency bounds.

        :return: allowances found in the source
        """

        async with self._semaphore:
            await self._random_delay()
            return await self.parse_source(source)

    async def _random_delay(self) -> None:
        """
        Sleep for a random duration to reduce request bursts.

        :return: None
        """

        delay = random.uniform(self.min_delay_seconds, self.max_delay_seconds)
        await asyncio.sleep(delay)

    def _client(self) -> httpx.AsyncClient:
        """
        Build an HTTP client with a rotated user agent header.

        :return: configured asynchronous HTTP client
        """

        agent = random.choice(self.user_agents)
        headers = {"User-Agent": agent.value}
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

        :return: parsed allowances from the source
        """
