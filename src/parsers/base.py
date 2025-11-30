import asyncio
import random
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from enum import Enum

from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from webdriver_manager.firefox import GeckoDriverManager

from src.models.dto.allowances import AllowanceDTO
from src.utils.logger import logger


class BrowserType(str, Enum):
    """
    Supported browser types for Selenium parser.
    """

    FIREFOX = "firefox"
    CHROME = "chrome"
    CHROMIUM = "chromium"


class BaseSeleniumParser(ABC):
    """
    Base Selenium parser with browser management and anti-detection.

    Provides infrastructure for web scraping using Chrome/Chromium/Firefox
    with stealth-like configuration to reduce bot detection.
    """

    # browser configuration
    HEADLESS: bool = True
    WINDOW_WIDTH: int = 1920
    WINDOW_HEIGHT: int = 1080
    PAGE_LOAD_TIMEOUT: int = 30
    ELEMENT_WAIT_TIMEOUT: int = 15

    # browser preference order
    BROWSER_PREFERENCE: tuple[BrowserType, ...] = (
        BrowserType.FIREFOX,
        BrowserType.CHROMIUM,
        BrowserType.CHROME,
    )

    # delay configuration for human-like behavior
    MIN_DELAY_SECONDS: float = 1.0
    MAX_DELAY_SECONDS: float = 3.0

    def __init__(self) -> None:
        self._driver: WebDriver | None = None
        self._parser_name = self.__class__.__name__

    @contextmanager
    def _browser_session(self):
        """
        Context manager for browser lifecycle.

        Creates browser on entry and ensures cleanup on exit.
        """

        logger.info(f"[{self._parser_name}] Starting browser session")

        try:
            self._create_browser()
            yield self._driver
        finally:
            self._close_browser()

    def _create_browser(self) -> None:
        """
        Create browser, trying each type in preference order.
        """

        logger.debug(f"[{self._parser_name}] Creating browser")

        last_error: Exception | None = None

        for browser_type in self.BROWSER_PREFERENCE:
            try:
                if browser_type == BrowserType.FIREFOX:
                    self._create_firefox_browser()
                elif browser_type == BrowserType.CHROMIUM:
                    self._create_chrome_browser(chromium=True)
                else:
                    self._create_chrome_browser(chromium=False)

                logger.info(
                    f"[{self._parser_name}] Browser created: {browser_type.value}"
                )
                return

            except Exception as e:
                last_error = e
                logger.debug(
                    f"[{self._parser_name}] {browser_type.value} failed: {e}"
                )
                continue

        raise WebDriverException(f"Could not create any browser: {last_error}")

    def _create_firefox_browser(self) -> None:
        """
        Create Firefox browser with anti-detection settings.
        """

        logger.debug(f"[{self._parser_name}] Trying Firefox browser")

        options = FirefoxOptions()

        if self.HEADLESS:
            options.add_argument("--headless")

        options.add_argument(f"--width={self.WINDOW_WIDTH}")
        options.add_argument(f"--height={self.WINDOW_HEIGHT}")

        # anti-detection preferences
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference("useAutomationExtension", False)
        options.set_preference("intl.accept_languages", "ru-RU, ru, en-US, en")
        options.set_preference("general.useragent.override", self._get_user_agent())

        service = FirefoxService(GeckoDriverManager().install())
        self._driver = webdriver.Firefox(service=service, options=options)
        self._driver.set_page_load_timeout(self.PAGE_LOAD_TIMEOUT)

    def _create_chrome_browser(self, chromium: bool = False) -> None:
        """
        Create Chrome/Chromium browser with anti-detection settings.

        :param chromium: use Chromium instead of Chrome
        """

        browser_name = "Chromium" if chromium else "Chrome"
        logger.debug(f"[{self._parser_name}] Trying {browser_name} browser")

        options = ChromeOptions()

        if self.HEADLESS:
            options.add_argument("--headless=new")

        options.add_argument(f"--window-size={self.WINDOW_WIDTH},{self.WINDOW_HEIGHT}")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--lang=ru-RU,ru")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-infobars")
        options.add_argument(f"--user-agent={self._get_user_agent()}")

        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        if chromium:
            service = ChromeService(
                ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()
            )
        else:
            service = ChromeService(ChromeDriverManager().install())

        self._driver = webdriver.Chrome(service=service, options=options)
        self._driver.set_page_load_timeout(self.PAGE_LOAD_TIMEOUT)

        # anti-detection JavaScript
        self._driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
                """
            },
        )

    @staticmethod
    def _get_user_agent() -> str:
        """
        Get realistic user agent string.

        :return: user agent string
        """

        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

    def _close_browser(self) -> None:
        """
        Safely close the browser and clean up resources.
        """

        if self._driver:
            logger.debug(f"[{self._parser_name}] Closing browser")
            try:
                self._driver.quit()
            except WebDriverException as e:
                logger.warning(f"[{self._parser_name}] Error closing browser: {e}")
            finally:
                self._driver = None

    def _navigate_to(self, url: str) -> bool:
        """
        Navigate to a URL with error handling.

        :param url: target URL
        :return: True if navigation succeeded
        """

        logger.debug(f"[{self._parser_name}] Navigating to: {url}")

        try:
            self._driver.get(url)
            self._random_delay()
            logger.debug(f"[{self._parser_name}] Successfully loaded: {url}")
            return True

        except TimeoutException:
            logger.error(f"[{self._parser_name}] Page load timeout: {url}")
            return False

        except WebDriverException as e:
            logger.error(f"[{self._parser_name}] Navigation error: {e}")
            return False

    def _wait_for_element(
        self,
        by: By,
        value: str,
        timeout: int | None = None,
    ) -> WebElement | None:
        """
        Wait for an element to be present and visible.

        :param by: locator strategy
        :param value: locator value
        :param timeout: wait timeout in seconds
        :return: found element or None
        """

        timeout = timeout or self.ELEMENT_WAIT_TIMEOUT

        try:
            element = WebDriverWait(self._driver, timeout).until(
                EC.visibility_of_element_located((by, value))
            )
            return element

        except TimeoutException:
            logger.debug(
                f"[{self._parser_name}] Element not found within {timeout}s: {value}"
            )
            return None

    def _wait_for_elements(
        self,
        by: By,
        value: str,
        timeout: int | None = None,
    ) -> list[WebElement]:
        """
        Wait for elements to be present.

        :param by: locator strategy
        :param value: locator value
        :param timeout: wait timeout in seconds
        :return: list of found elements
        """

        timeout = timeout or self.ELEMENT_WAIT_TIMEOUT

        try:
            WebDriverWait(self._driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return self._driver.find_elements(by, value)

        except TimeoutException:
            logger.debug(
                f"[{self._parser_name}] Elements not found within {timeout}s: {value}"
            )
            return []

    def _find_element_safe(self, by: By, value: str) -> WebElement | None:
        """
        Find element without throwing exception if not found.

        :param by: locator strategy
        :param value: locator value
        :return: found element or None
        """

        try:
            return self._driver.find_element(by, value)
        except NoSuchElementException:
            return None

    def _find_elements_safe(self, by: By, value: str) -> list[WebElement]:
        """
        Find elements without throwing exception if not found.

        :param by: locator strategy
        :param value: locator value
        :return: list of found elements
        """

        try:
            return self._driver.find_elements(by, value)
        except NoSuchElementException:
            return []

    def _click_element(self, element: WebElement) -> bool:
        """
        Click an element with error handling.

        :param element: element to click
        :return: True if click succeeded
        """

        try:
            element.click()
            self._random_delay()
            return True

        except WebDriverException as e:
            logger.warning(f"[{self._parser_name}] Click failed: {e}")
            return False

    def _send_keys(self, element: WebElement, text: str) -> bool:
        """
        Send keys to an element.

        :param element: input element
        :param text: text to type
        :return: True if successful
        """

        try:
            element.clear()
            element.send_keys(text)
            self._random_delay()
            return True

        except WebDriverException as e:
            logger.warning(f"[{self._parser_name}] Send keys failed: {e}")
            return False

    def _scroll_to_element(self, element: WebElement) -> None:
        """
        Scroll element into view.

        :param element: element to scroll to
        """

        self._driver.execute_script(
            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
            element,
        )
        self._random_delay(min_delay=0.3, max_delay=0.8)

    def _scroll_to_bottom(self) -> None:
        """
        Scroll to the bottom of the page.
        """

        self._driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        self._random_delay()

    def _get_page_source(self) -> str:
        """
        Get current page HTML source.

        :return: page source HTML
        """

        return self._driver.page_source

    def _get_current_url(self) -> str:
        """
        Get current page URL.

        :return: current URL
        """

        return self._driver.current_url

    def _random_delay(
        self,
        min_delay: float | None = None,
        max_delay: float | None = None,
    ) -> None:
        """
        Sleep for a random duration to simulate human behavior.

        :param min_delay: minimum delay in seconds
        :param max_delay: maximum delay in seconds
        """

        min_d = min_delay or self.MIN_DELAY_SECONDS
        max_d = max_delay or self.MAX_DELAY_SECONDS
        delay = random.uniform(min_d, max_d)
        time.sleep(delay)

    def run(self) -> list[AllowanceDTO]:
        """
        Execute the parsing lifecycle and return normalized allowances.

        :return: list of parsed allowances
        """

        logger.info(f"[{self._parser_name}] Starting parsing process")

        with self._browser_session():
            try:
                sources = self.discover_sources()
                logger.info(
                    f"[{self._parser_name}] Discovered {len(sources)} sources to parse"
                )

                if not sources:
                    logger.warning(
                        f"[{self._parser_name}] No sources found, returning empty list"
                    )
                    return []

                allowances: list[AllowanceDTO] = []

                for idx, source in enumerate(sources, start=1):
                    logger.info(
                        f"[{self._parser_name}] Parsing source {idx}/{len(sources)}: {source}"
                    )

                    try:
                        parsed = self.parse_source(source=source)
                        allowances.extend(parsed)
                        logger.debug(
                            f"[{self._parser_name}] Extracted {len(parsed)} allowances"
                        )
                    except Exception as e:
                        logger.error(
                            f"[{self._parser_name}] Failed to parse source {idx}: {e}"
                        )

                logger.info(
                    f"[{self._parser_name}] Parsing completed: "
                    f"{len(allowances)} total allowances extracted"
                )

                return allowances

            except Exception as e:
                logger.error(f"[{self._parser_name}] Critical error: {e}")
                raise

    async def run_async(self) -> list[AllowanceDTO]:
        """
        Async wrapper for running parser in thread pool.

        :return: list of parsed allowances
        """

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.run)

    @abstractmethod
    def discover_sources(self) -> list[str]:
        """
        Discover source URLs or identifiers to parse.

        :return: list of sources for parsing
        """

    @abstractmethod
    def parse_source(self, source: str) -> list[AllowanceDTO]:
        """
        Parse allowance data from a source.

        :param source: source URL or identifier
        :return: parsed allowances from the source
        """

    @staticmethod
    def normalize_text(value: str) -> str:
        """
        Normalize text by collapsing whitespace and trimming.

        :param value: raw text
        :return: cleaned text
        """

        return " ".join(value.split()).strip()
