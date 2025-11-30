import re
from dataclasses import dataclass
from enum import StrEnum

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By

from src.models.dto.allowances import AllowanceDTO
from src.parsers.base import BaseSeleniumParser
from src.utils.logger import logger


class ProgramLevel(StrEnum):
    """
    Program jurisdiction level.
    """

    FEDERAL = "Федеральная"
    REGIONAL = "Региональная"


@dataclass(frozen=True, slots=True)
class CssSelectors:
    """
    CSS selectors for dom.rf program cards.
    """

    # catalog page selectors
    CATALOG_TITLE: str = ".program-directory__title, h1"
    PROGRAM_CARD_LINK: str = "a.program-directory__category-item"
    PROGRAM_LEVEL_BADGE: str = ".program-directory__category-type-item.green.active p"

    # detail page selectors
    DETAIL_TITLE: str = "h1.program-directory__detail-title"
    DETAIL_TAGS: str = "div.program-directory__tags-item"
    REGULATION_SECTION: str = "div.information-block-document"
    REGULATION_LINK: str = "a.information-block-document__title"


class DomRfParser(BaseSeleniumParser):
    """
    Selenium-based parser for extracting government support programs from dom.rf.

    Parses the official catalog at спроси.дом.рф/catalog/ to extract
    social support programs with their regulating laws and target categories.
    """

    # base URL (punycode for спроси.дом.рф)
    BASE_URL: str = "https://xn--h1alcedd.xn--d1aqf.xn--p1ai"
    CATALOG_URL: str = f"{BASE_URL}/catalog/"

    # domain for URL validation
    _DOMAIN: str = "xn--h1alcedd.xn--d1aqf.xn--p1ai"

    # URL patterns to exclude (region listing pages, not program cards)
    _EXCLUDED_URL_PATTERNS: tuple[str, ...] = (
        "/catalog/region-is-",
        "/catalog/?",
    )

    # regex patterns for law number extraction
    _LAW_NUMBER_PATTERNS: tuple[re.Pattern[str], ...] = (
        re.compile(r"№\s*(\d+(?:-ФЗ|-П|-н))", re.IGNORECASE),
        re.compile(r"(\d+)-ФЗ", re.IGNORECASE),
        re.compile(r"(\d+)-П", re.IGNORECASE),
    )

    def __init__(self) -> None:
        super().__init__()
        self._selectors = CssSelectors()
        self._program_levels: dict[str, str] = {}
        self._max_items: int | None = None

    def set_max_items(self, limit: int) -> None:
        """
        Set maximum number of items to parse.

        :param limit: maximum number of programs to parse
        """

        self._max_items = limit

    def discover_sources(self) -> list[str]:
        """
        Navigate to catalog and collect program card URLs.

        :return: list of program card URLs to parse
        """

        logger.info(f"[{self._parser_name}] Navigating to catalog: {self.CATALOG_URL}")

        if not self._navigate_to(url=self.CATALOG_URL):
            logger.error(f"[{self._parser_name}] Failed to load catalog")
            return []

        # wait for catalog content to load
        self._wait_for_element(
            by=By.CSS_SELECTOR,
            value=self._selectors.CATALOG_TITLE,
            timeout=15,
        )

        logger.info(f"[{self._parser_name}] Catalog loaded: {self._get_current_url()}")

        # collect program cards with their levels
        program_urls = self._collect_program_cards()
        logger.info(f"[{self._parser_name}] Found {len(program_urls)} program cards")

        return program_urls

    def _collect_program_cards(self) -> list[str]:
        """
        Collect program card URLs and their levels from catalog page.

        :return: list of unique program URLs
        """

        urls: list[str] = []

        # scroll to load all content
        self._scroll_to_bottom()

        # parse page source with BeautifulSoup for structured extraction
        html = self._get_page_source()
        soup = BeautifulSoup(html, "html.parser")

        # find all program card links
        card_links = soup.select(self._selectors.PROGRAM_CARD_LINK)
        logger.debug(f"[{self._parser_name}] Found {len(card_links)} card elements")

        for card in card_links:
            href = card.get("href")
            if not href or not isinstance(href, str):
                continue

            # convert relative URL to absolute
            if href.startswith("/"):
                full_url = f"{self.BASE_URL}{href}"
            else:
                full_url = href

            # skip excluded patterns
            if self._is_excluded_url(url=full_url):
                continue

            # extract program level from card
            level_elem = card.select_one(self._selectors.PROGRAM_LEVEL_BADGE)
            if level_elem:
                level_text = self.normalize_text(value=level_elem.get_text())
                self._program_levels[full_url] = level_text

            urls.append(full_url)

        # deduplicate while preserving order
        seen: set[str] = set()
        unique_urls: list[str] = []
        for url in urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        # apply max_items limit if set
        if self._max_items is not None:
            unique_urls = unique_urls[:self._max_items]
            logger.info(
                f"[{self._parser_name}] Limited to {self._max_items} items for testing"
            )

        return unique_urls

    def _is_excluded_url(self, url: str) -> bool:
        """
        Check if URL should be excluded from parsing.

        :param url: URL to check
        :return: True if URL should be excluded
        """

        for pattern in self._EXCLUDED_URL_PATTERNS:
            if pattern in url:
                return True

        # must be from correct domain
        if self._DOMAIN not in url and not url.startswith("/catalog/"):
            return True

        # skip catalog root
        if url.rstrip("/").endswith("/catalog"):
            return True

        return False

    def parse_source(self, source: str) -> list[AllowanceDTO]:
        """
        Parse a single program card page.

        :param source: program card URL
        :return: list with one AllowanceDTO or empty list
        """

        logger.debug(f"[{self._parser_name}] Parsing program card: {source}")

        if not self._navigate_to(url=source):
            logger.warning(f"[{self._parser_name}] Failed to load: {source}")
            return []

        # wait for main title to appear
        self._wait_for_element(
            by=By.CSS_SELECTOR,
            value=self._selectors.DETAIL_TITLE,
            timeout=10,
        )

        html = self._get_page_source()
        soup = BeautifulSoup(html, "html.parser")

        allowance = self._parse_program_card(soup=soup, url=source)

        if allowance:
            logger.info(
                f"[{self._parser_name}] Extracted: {allowance.name[:50]}... | "
                f"NPA: {allowance.npa_number} | Level: {allowance.level}"
            )
            return [allowance]

        logger.debug(f"[{self._parser_name}] No valid data extracted from: {source}")
        return []

    def _parse_program_card(self, soup: BeautifulSoup, url: str) -> AllowanceDTO | None:
        """
        Parse program card page for allowance data.

        :param soup: parsed HTML document
        :param url: source URL for fallback ID generation
        :return: parsed AllowanceDTO or None if required fields missing
        """

        name = self._extract_program_name(soup=soup)
        if not name:
            return None

        npa_number, npa_name = self._extract_regulation_info(soup=soup)
        if not npa_number:
            npa_number = self._generate_fallback_id(url=url)

        if not npa_number:
            return None

        # get level from pre-extracted data or from page
        level = self._program_levels.get(url) or self._extract_level_from_page(soup=soup)

        subjects = self._extract_program_tags(soup=soup)

        return AllowanceDTO(
            name=name,
            npa_number=npa_number,
            npa_name=npa_name,
            level=level,
            subjects=subjects,
        )

    def _extract_program_name(self, soup: BeautifulSoup) -> str:
        """
        Extract program name from page title.

        :param soup: parsed HTML document
        :return: program name or empty string
        """

        # primary: specific title element
        title_elem = soup.select_one(self._selectors.DETAIL_TITLE)
        if title_elem:
            name = self.normalize_text(value=title_elem.get_text())
            if len(name) > 5:
                return name

        # fallback: any h1
        h1 = soup.find("h1")
        if h1:
            name = self.normalize_text(value=h1.get_text())
            if len(name) > 5:
                return name

        return ""

    def _extract_level_from_page(self, soup: BeautifulSoup) -> str | None:
        """
        Extract program level from detail page.

        :param soup: parsed HTML document
        :return: program level or None
        """

        # look for level badge on detail page
        level_elem = soup.select_one(".program-directory__tags-item.active")
        if level_elem:
            text = self.normalize_text(value=level_elem.get_text()).lower()
            if "федеральн" in text:
                return ProgramLevel.FEDERAL
            if "региональн" in text:
                return ProgramLevel.REGIONAL

        # search in page text as fallback
        page_text = soup.get_text().lower()
        if "федеральная программа" in page_text:
            return ProgramLevel.FEDERAL
        if "региональная программа" in page_text:
            return ProgramLevel.REGIONAL

        return None

    def _extract_regulation_info(self, soup: BeautifulSoup) -> tuple[str, str | None]:
        """
        Extract law number and full name from "Программа регулируется" section.

        :param soup: parsed HTML document
        :return: tuple of (law_number, full_law_name)
        """

        # find regulation section
        regulation_section = soup.select_one(self._selectors.REGULATION_SECTION)
        if not regulation_section:
            return self._fallback_regulation_search(soup=soup)

        # extract from the document link
        law_link = regulation_section.select_one(self._selectors.REGULATION_LINK)
        if not law_link:
            return self._fallback_regulation_search(soup=soup)

        full_law_text = self.normalize_text(value=law_link.get_text())
        npa_number = self._extract_law_number(text=full_law_text)

        if npa_number:
            return npa_number, full_law_text if len(full_law_text) > 20 else None

        return self._fallback_regulation_search(soup=soup)

    def _fallback_regulation_search(self, soup: BeautifulSoup) -> tuple[str, str | None]:
        """
        Search entire page for law information as fallback.

        :param soup: parsed HTML document
        :return: tuple of (law_number, full_law_name)
        """

        page_text = soup.get_text()
        npa_number = self._extract_law_number(text=page_text)

        if not npa_number:
            return "", None

        npa_name = self._extract_full_law_name(text=page_text)
        return npa_number, npa_name

    def _extract_law_number(self, text: str) -> str:
        """
        Extract law number from text using regex patterns.

        :param text: text to search
        :return: extracted law number or empty string
        """

        for pattern in self._LAW_NUMBER_PATTERNS:
            match = pattern.search(text)
            if match:
                return self.normalize_text(value=match.group())

        return ""

    def _extract_full_law_name(self, text: str) -> str | None:
        """
        Extract full law name from text.

        :param text: text to search
        :return: full law name or None
        """

        law_patterns = (
            r"Федеральный закон[^«»\n]*(?:«[^»]+»)?[^\.]{10,}",
            r"Постановление Правительства[^«»\n]*(?:«[^»]+»)?[^\.]{10,}",
            r"Указ Президента[^«»\n]*(?:«[^»]+»)?[^\.]{10,}",
        )

        for pattern in law_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                law_name = self.normalize_text(value=match.group())
                if len(law_name) > 30:
                    return law_name[:500]

        return None

    def _generate_fallback_id(self, url: str) -> str:
        """
        Generate program ID from URL slug as fallback.

        :param url: program URL
        :return: generated ID or empty string
        """

        match = re.search(r"/catalog/([a-z0-9\-_]+)/?$", url.lower())
        if match:
            slug = match.group(1)
            if len(slug) > 3:
                return f"CATALOG-{slug[:30].upper()}"

        return ""

    def _extract_program_tags(self, soup: BeautifulSoup) -> list[str] | None:
        """
        Extract program tags/categories from the page.

        :param soup: parsed HTML document
        :return: list of tags or None
        """

        tags: list[str] = []

        # primary: extract from tag elements
        tag_elements = soup.select(self._selectors.DETAIL_TAGS)
        for elem in tag_elements:
            tag_text = self.normalize_text(value=elem.get_text())
            # exclude level tags from subjects
            if tag_text and len(tag_text) > 2:
                lower_text = tag_text.lower()
                if "федеральн" not in lower_text and "региональн" not in lower_text:
                    tags.append(tag_text)

        if tags:
            return tags

        # fallback: search for participant section
        return self._extract_participants_fallback(soup=soup)

    def _extract_participants_fallback(self, soup: BeautifulSoup) -> list[str] | None:
        """
        Extract participant categories as fallback for tags.

        :param soup: parsed HTML document
        :return: list of participant categories or None
        """

        participants: list[str] = []
        search_keywords = ("кто может", "участники", "получатели", "категории граждан")

        for elem in soup.find_all(["h2", "h3", "p"]):
            text = elem.get_text().lower()
            if not any(kw in text for kw in search_keywords):
                continue

            # found section header - extract from following list
            next_ul = elem.find_next("ul")
            if not next_ul:
                continue

            for li in next_ul.find_all("li", limit=10):
                participant = self.normalize_text(value=li.get_text())
                if 3 < len(participant) < 100:
                    participants.append(participant)

            if participants:
                break

        return participants if participants else None
