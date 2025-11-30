import re
import time

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from src.models.dto.allowances import AllowanceDTO
from src.parsers.base import BaseSeleniumParser
from src.utils.logger import logger


class DomRfParser(BaseSeleniumParser):
    """
    Selenium-based parser for extracting allowance data from Dom.rf.

    Uses search functionality and section navigation to discover
    social support measures, subsidies, and benefits.
    """

    BASE_URL: str = "https://xn--d1aqf.xn--p1ai"

    # search queries for discovering relevant content
    SEARCH_QUERIES: tuple[str, ...] = (
        "меры поддержки",
        "материнский капитал",
        "субсидии на жилье",
        "льготная ипотека",
        "социальные пособия",
    )

    # known sections with support measures
    KNOWN_SECTIONS: tuple[str, ...] = (
        "/programmes/",
        "/gospodderzhka/",
        "/subsidies/",
    )

    # max pages to parse per search query
    MAX_PAGES_PER_QUERY: int = 5

    def __init__(self) -> None:
        super().__init__()
        self._collected_urls: set[str] = set()

    def discover_sources(self) -> list[str]:
        """
        Discover relevant pages using search and known sections.

        :return: list of unique URLs to parse
        """

        logger.info(f"[{self._parser_name}] Starting source discovery")

        # navigate to main page first
        if not self._navigate_to(self.BASE_URL):
            logger.error(f"[{self._parser_name}] Failed to load main page")
            return []

        # wait for page to fully load
        time.sleep(2)
        logger.info(f"[{self._parser_name}] Main page loaded: {self._get_current_url()}")

        # try search-based discovery
        self._discover_via_search()

        # try known sections
        self._discover_via_sections()

        # try finding links from main page
        self._discover_from_current_page()

        urls = list(self._collected_urls)
        logger.info(f"[{self._parser_name}] Total unique sources discovered: {len(urls)}")

        return urls

    def _discover_via_search(self) -> None:
        """
        Discover sources by searching for relevant keywords.
        """

        logger.info(f"[{self._parser_name}] Attempting search-based discovery")

        for query in self.SEARCH_QUERIES:
            logger.debug(f"[{self._parser_name}] Searching for: '{query}'")

            # try to find search input
            search_input = self._find_search_input()

            if search_input:
                self._perform_search(search_input=search_input, query=query)
            else:
                logger.debug(f"[{self._parser_name}] Search input not found, skipping")
                break

    def _find_search_input(self) -> any:
        """
        Find search input element on the page.

        :return: search input element or None
        """

        # common search input selectors
        selectors = [
            "input[type='search']",
            "input[name='q']",
            "input[name='query']",
            "input[name='search']",
            "input[placeholder*='Поиск']",
            "input[placeholder*='поиск']",
            ".search-input",
            "#search-input",
            "[data-search-input]",
        ]

        for selector in selectors:
            element = self._find_element_safe(by=By.CSS_SELECTOR, value=selector)
            if element:
                logger.debug(f"[{self._parser_name}] Found search input: {selector}")
                return element

        # try clicking search button first
        search_buttons = [
            "[data-search-button]",
            ".search-button",
            "button[aria-label*='Поиск']",
            ".header-search",
            "[class*='search']",
        ]

        for selector in search_buttons:
            button = self._find_element_safe(by=By.CSS_SELECTOR, value=selector)
            if button:
                try:
                    self._click_element(element=button)
                    time.sleep(1)

                    # now try to find search input again
                    for input_sel in selectors:
                        element = self._find_element_safe(
                            by=By.CSS_SELECTOR, value=input_sel
                        )
                        if element:
                            return element
                except Exception:
                    continue

        return None

    def _perform_search(self, search_input, query: str) -> None:
        """
        Perform search and collect result URLs.

        :param search_input: search input element
        :param query: search query
        """

        try:
            search_input.clear()
            search_input.send_keys(query)
            search_input.send_keys(Keys.RETURN)
            time.sleep(2)

            logger.debug(
                f"[{self._parser_name}] Search performed, current URL: {self._get_current_url()}"
            )

            # collect URLs from search results
            self._collect_links_from_page()

            # handle pagination
            pages_processed = 1
            while pages_processed < self.MAX_PAGES_PER_QUERY:
                if not self._go_to_next_page():
                    break
                self._collect_links_from_page()
                pages_processed += 1

            logger.debug(
                f"[{self._parser_name}] Processed {pages_processed} pages for query '{query}'"
            )

            # go back to main page for next search
            self._navigate_to(self.BASE_URL)
            time.sleep(1)

        except Exception as e:
            logger.warning(f"[{self._parser_name}] Search failed for '{query}': {e}")

    def _discover_via_sections(self) -> None:
        """
        Discover sources from known site sections.
        """

        logger.info(f"[{self._parser_name}] Checking known sections")

        for section in self.KNOWN_SECTIONS:
            url = f"{self.BASE_URL}{section}"
            logger.debug(f"[{self._parser_name}] Checking section: {url}")

            if self._navigate_to(url):
                time.sleep(1)

                # check if page loaded successfully (not 404)
                current_url = self._get_current_url()
                if "404" not in current_url and "error" not in current_url.lower():
                    self._collect_links_from_page()
                    self._collected_urls.add(current_url)

    def _discover_from_current_page(self) -> None:
        """
        Collect relevant links from current page.
        """

        self._navigate_to(self.BASE_URL)
        time.sleep(1)
        self._collect_links_from_page()

    def _collect_links_from_page(self) -> None:
        """
        Collect relevant links from current page.
        """

        links = self._find_elements_safe(by=By.TAG_NAME, value="a")

        for link in links:
            try:
                href = link.get_attribute("href")
                text = link.text.lower() if link.text else ""

                if self._is_relevant_link(href=href, text=text):
                    self._collected_urls.add(href)

            except Exception:
                continue

    def _is_relevant_link(self, href: str | None, text: str) -> bool:
        """
        Check if a link is relevant to social support content.

        :param href: link URL
        :param text: link text
        :return: True if link is relevant
        """

        if not href:
            return False

        # must be from same domain
        if not href.startswith(self.BASE_URL):
            return False

        # skip static resources
        skip_patterns = [
            "/static/",
            "/assets/",
            "/images/",
            ".pdf",
            ".jpg",
            ".png",
            ".css",
            ".js",
            "#",
            "javascript:",
        ]

        href_lower = href.lower()
        for pattern in skip_patterns:
            if pattern in href_lower:
                return False

        # check for relevant keywords in URL or text
        relevant_keywords = [
            "поддержк",
            "пособ",
            "субсид",
            "льгот",
            "ипотек",
            "капитал",
            "семь",
            "выплат",
            "программ",
            "господдержк",
            "соцподдержк",
            "материнск",
            "жиль",
            "недвижим",
        ]

        combined = f"{href_lower} {text}"
        return any(keyword in combined for keyword in relevant_keywords)

    def _go_to_next_page(self) -> bool:
        """
        Navigate to next page in pagination.

        :return: True if navigation succeeded
        """

        next_selectors = [
            "a[rel='next']",
            ".pagination__next",
            ".next-page",
            "[aria-label='Следующая']",
            "a:contains('Далее')",
            ".pagination a:last-child",
        ]

        for selector in next_selectors:
            try:
                next_btn = self._find_element_safe(by=By.CSS_SELECTOR, value=selector)
                if next_btn and next_btn.is_displayed():
                    self._click_element(element=next_btn)
                    time.sleep(2)
                    return True
            except Exception:
                continue

        return False

    def parse_source(self, source: str) -> list[AllowanceDTO]:
        """
        Parse a Dom.rf page for allowances.

        :param source: URL to parse
        :return: list of allowances from the page
        """

        logger.debug(f"[{self._parser_name}] Parsing source: {source}")

        if not self._navigate_to(source):
            logger.warning(f"[{self._parser_name}] Failed to load: {source}")
            return []

        time.sleep(1)

        # get page source for BeautifulSoup parsing
        html = self._get_page_source()
        soup = BeautifulSoup(html, "html.parser")

        allowances: list[AllowanceDTO] = []

        # extract from page structure
        candidates = self._extract_candidates(soup=soup)
        logger.debug(f"[{self._parser_name}] Found {len(candidates)} candidates")

        for candidate in candidates:
            name = self.normalize_text(value=candidate.get("name", ""))
            npa_number = self._normalize_npa(value=candidate.get("npa_number", ""))
            subjects = self._normalize_subjects(values=candidate.get("subjects", []))

            if name and npa_number:
                allowances.append(
                    AllowanceDTO(
                        name=name,
                        npa_number=npa_number,
                        subjects=subjects,
                    )
                )
                logger.debug(
                    f"[{self._parser_name}] Extracted: '{name[:50]}...' | NPA: {npa_number}"
                )

        # also try to extract from main content
        main_content = self._extract_main_content_allowance(soup=soup, source=source)
        if main_content:
            allowances.append(main_content)

        logger.info(
            f"[{self._parser_name}] Extracted {len(allowances)} allowances from {source}"
        )

        return allowances

    def _extract_candidates(
        self,
        soup: BeautifulSoup,
    ) -> list[dict[str, str | list[str]]]:
        """
        Extract raw allowance blocks from parsed HTML.

        :param soup: parsed HTML document
        :return: list of candidate dictionaries
        """

        results: list[dict[str, str | list[str]]] = []

        # extract from headers with NPA numbers
        headers = soup.find_all(["h1", "h2", "h3", "h4"])
        logger.debug(f"[{self._parser_name}] Analyzing {len(headers)} headers")

        for header in headers:
            text = self.normalize_text(value=header.get_text(separator=" "))
            if not text:
                continue

            npa_number = self._find_npa_number(text=text)
            if npa_number:
                subjects = self._find_subjects(header=header)
                results.append({
                    "name": text,
                    "npa_number": npa_number,
                    "subjects": subjects,
                })

        # extract from spans with law data
        law_spans = soup.find_all("span", attrs={"data-law-number": True})
        logger.debug(f"[{self._parser_name}] Found {len(law_spans)} law spans")

        for span in law_spans:
            npa_number = self._normalize_npa(value=span.get("data-law-number", ""))
            name = self.normalize_text(value=span.get_text())
            if npa_number and name:
                results.append({
                    "name": name,
                    "npa_number": npa_number,
                    "subjects": [],
                })

        # extract from article/card structures
        cards = soup.find_all(class_=lambda x: x and any(
            kw in str(x).lower() for kw in ["card", "item", "article", "block"]
        ))

        for card in cards:
            text = self.normalize_text(value=card.get_text(separator=" "))
            npa_number = self._find_npa_number(text=text)

            if npa_number:
                # try to find title within card
                title_elem = card.find(["h1", "h2", "h3", "h4", "h5"])
                if title_elem:
                    name = self.normalize_text(value=title_elem.get_text())
                    if name:
                        results.append({
                            "name": name,
                            "npa_number": npa_number,
                            "subjects": [],
                        })

        return results

    def _extract_main_content_allowance(
        self,
        soup: BeautifulSoup,
        source: str,
    ) -> AllowanceDTO | None:
        """
        Try to extract allowance from main page content.

        :param soup: parsed HTML
        :param source: source URL
        :return: extracted allowance or None
        """

        # find main title
        title = soup.find("h1")
        if not title:
            return None

        title_text = self.normalize_text(value=title.get_text())
        if not title_text:
            return None

        # check if this looks like an allowance page
        relevant_keywords = [
            "поддержк", "пособ", "субсид", "льгот", "ипотек",
            "капитал", "выплат", "программ",
        ]

        title_lower = title_text.lower()
        if not any(kw in title_lower for kw in relevant_keywords):
            return None

        # try to find NPA number in page
        page_text = soup.get_text()
        npa_number = self._find_npa_number(text=page_text)

        if not npa_number:
            # generate synthetic NPA from URL
            npa_number = self._generate_npa_from_url(url=source)

        if not npa_number:
            return None

        # extract description from meta or first paragraph
        description = []
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            description.append(self.normalize_text(value=meta_desc["content"]))

        # get first few paragraphs after title
        paragraphs = title.find_all_next("p", limit=3)
        for p in paragraphs:
            text = self.normalize_text(value=p.get_text())
            if text and len(text) < 300:
                description.append(text)

        subjects = description[:5] if description else None

        logger.debug(
            f"[{self._parser_name}] Extracted main content: '{title_text[:50]}...'"
        )

        return AllowanceDTO(
            name=title_text,
            npa_number=npa_number,
            subjects=subjects,
        )

    def _normalize_npa(self, value: str) -> str:
        """
        Normalize NPA number formatting.

        :param value: raw NPA number
        :return: cleaned NPA number
        """

        cleaned = self.normalize_text(value=value)
        cleaned = cleaned.replace("№", "№ ")
        return " ".join(cleaned.split())

    def _normalize_subjects(self, values: list[str]) -> list[str] | None:
        """
        Normalize subject descriptors.

        :param values: raw subject strings
        :return: cleaned subjects or None
        """

        cleaned = [
            self.normalize_text(value=v)
            for v in values
            if self.normalize_text(value=v)
        ]
        return cleaned[:10] if cleaned else None

    @staticmethod
    def _find_npa_number(text: str) -> str:
        """
        Find NPA number pattern in text.

        :param text: text to search
        :return: extracted NPA number or empty string
        """

        # patterns for legal document numbers
        patterns = [
            r"№\s?[A-Za-zА-Яа-я0-9\-/]+",
            r"Федеральный закон\s+№?\s?[\d\-]+",
            r"Постановление\s+№?\s?[\d\-]+",
            r"Закон\s+№?\s?[\d\-]+",
            r"\d+-ФЗ",
            r"\d+-П",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group()

        return ""

    def _find_subjects(self, header) -> list[str]:
        """
        Find subject descriptors near a header.

        :param header: BeautifulSoup header element
        :return: list of subject descriptions
        """

        subjects: list[str] = []

        for sibling in header.find_all_next(["p", "li", "div"], limit=5):
            # skip if it's another header
            if sibling.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                break

            text = self.normalize_text(value=sibling.get_text())
            if text and 10 < len(text) < 300:
                subjects.append(text)

        return subjects[:5]

    @staticmethod
    def _generate_npa_from_url(url: str) -> str:
        """
        Generate a synthetic NPA identifier from URL.

        :param url: source URL
        :return: synthetic NPA or empty string
        """

        # extract meaningful part from URL
        match = re.search(r"/([a-z0-9\-]+)/?$", url.lower())
        if match:
            slug = match.group(1)
            if len(slug) > 3:
                return f"DOMRF-{slug.upper()[:20]}"

        return ""
