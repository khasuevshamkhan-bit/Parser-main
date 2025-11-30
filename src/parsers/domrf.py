import re
from dataclasses import dataclass
from datetime import datetime
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
    PARTICIPANT_TAB: str = "div.tab-panel[data-tab-panel='Требования к участнику']"


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
                f"Regulation: {allowance.npa_name[:80]} | Level: {allowance.level}"
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

        npa_name = self._extract_regulation_text(soup=soup)
        if not npa_name:
            return None

        # get level from pre-extracted data or from page
        level = self._program_levels.get(url) or self._extract_level_from_page(soup=soup)

        validity_period, is_active = self._extract_validity_period(soup=soup)
        if not is_active:
            logger.info(
                f"[{self._parser_name}] Skipping expired program: {name[:50]}..."
            )
            return None

        subjects = self._extract_participants(soup=soup)

        return AllowanceDTO(
            name=name,
            npa_name=npa_name,
            level=level,
            subjects=subjects,
            validity_period=validity_period,
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

    def _extract_regulation_text(self, soup: BeautifulSoup) -> str:
        """
        Extract full text from the "Программа регулируется" section.

        :param soup: parsed HTML document
        :return: normalized regulation text or empty string
        """

        regulation_section = soup.select_one(self._selectors.REGULATION_SECTION)
        if not regulation_section:
            return ""

        regulation_texts: list[str] = []

        for link in regulation_section.select(self._selectors.REGULATION_LINK):
            text = self.normalize_text(value=link.get_text())
            if text:
                regulation_texts.append(text)

        if regulation_texts:
            # remove duplicates while preserving order
            seen: set[str] = set()
            unique_texts: list[str] = []
            for text in regulation_texts:
                if text not in seen:
                    seen.add(text)
                    unique_texts.append(text)

            joined = "; ".join(unique_texts)
            return joined[:512]

        body_text = self.normalize_text(value=regulation_section.get_text(" "))
        return body_text[:512]

    def _extract_validity_period(self, soup: BeautifulSoup) -> tuple[str | None, bool]:
        """
        Extract validity period from page tags and determine if program is active.

        :param soup: parsed HTML document
        :return: tuple of (validity text, is_active)
        """

        today = datetime.today().date()

        for elem in soup.select(self._selectors.DETAIL_TAGS):
            tag_text = self.normalize_text(value=elem.get_text())
            if not tag_text:
                continue

            lower = tag_text.lower()
            if not any(keyword in lower for keyword in ("действует", "заверш")):
                continue

            end_date = self._extract_date(tag_text)

            if "заверш" in lower:
                is_active = end_date is not None and end_date >= today
                return tag_text, is_active

            if end_date and end_date < today:
                return tag_text, False

            return tag_text, True

        return None, True

    @staticmethod
    def _extract_date(text: str) -> datetime.date | None:
        """
        Parse first date in DD.MM.YYYY format from text.

        :param text: text to scan
        :return: date object or None
        """

        match = re.search(r"(\d{2}\.\d{2}\.\d{4})", text)
        if not match:
            return None

        try:
            return datetime.strptime(match.group(1), "%d.%m.%Y").date()
        except ValueError:
            return None

    def _extract_participants(self, soup: BeautifulSoup) -> list[str] | None:
        """
        Extract participant categories from the dedicated tab.

        :param soup: parsed HTML document
        :return: list of participant descriptions or None
        """

        participants: list[str] = []

        participant_panel = soup.select_one(self._selectors.PARTICIPANT_TAB)
        if participant_panel:
            for li in participant_panel.find_all("li"):
                participant = self.normalize_text(value=li.get_text())
                if 3 < len(participant) < 300:
                    participants.append(participant)

            if not participants:
                panel_text = self.normalize_text(
                    value=participant_panel.get_text(" ", strip=True)
                )
                if panel_text:
                    participants.append(panel_text)

        if not participants:
            participants = self._extract_participants_fallback(soup=soup) or []

        return participants if participants else None

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
