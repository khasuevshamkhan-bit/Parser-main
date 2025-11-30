import re
import xml.etree.ElementTree as etree

import httpx
from bs4 import BeautifulSoup

from src.models.dto.allowances import AllowanceDTO
from src.parsers.base import BaseParser
from src.utils.logger import logger


class DomRfParser(BaseParser):
    """
    Parser tailored for extracting allowance data from Dom.rf pages.

    Scrapes the Dom.rf website for social support information,
    subsidies, benefits, and related legal documents.
    """

    # keywords used to filter relevant URLs from sitemap
    KEYWORDS: tuple[str, ...] = ("поддерж", "субсид", "пособ", "ипотек", "льгот")

    def __init__(
            self,
            base_url: str = "https://xn--d1aqf.xn--p1ai",
    ) -> None:
        """
        Initialize the Dom.rf parser.

        :param base_url: root URL of the Dom.rf website without trailing slash
        """

        super().__init__()
        self._base_url = base_url.rstrip("/")
        self._sitemap_url = f"{self._base_url}/sitemap.xml"

        logger.debug(f"[{self._parser_name}] Initialized with base URL: {self._base_url}")
        logger.debug(f"[{self._parser_name}] Sitemap URL: {self._sitemap_url}")

    async def fetch_sources(self) -> list[str]:
        """
        Discover candidate Dom.rf URLs containing social support information.

        Fetches the sitemap and filters URLs by relevant keywords.

        :return: filtered list of URLs to parse
        """

        logger.info(f"[{self._parser_name}] Fetching sitemap from {self._sitemap_url}")

        async with self._create_client() as client:
            try:
                response = await client.get(self._sitemap_url)
                logger.debug(
                    f"[{self._parser_name}] Sitemap response: "
                    f"status={response.status_code}, size={len(response.content)} bytes"
                )

                if response.status_code != httpx.codes.OK:
                    logger.warning(
                        f"[{self._parser_name}] Sitemap fetch failed with status "
                        f"{response.status_code}, falling back to base URL"
                    )
                    return [self._base_url]

            except httpx.HTTPError as e:
                logger.error(f"[{self._parser_name}] HTTP error fetching sitemap: {e}")
                return [self._base_url]

        try:
            tree = etree.fromstring(response.content)
            logger.debug(f"[{self._parser_name}] Sitemap XML parsed successfully")
        except etree.ParseError as e:
            logger.error(f"[{self._parser_name}] Failed to parse sitemap XML: {e}")
            return [self._base_url]

        # extract all URLs from sitemap
        all_urls = self._extract_urls_from_sitemap(tree=tree)
        logger.info(f"[{self._parser_name}] Found {len(all_urls)} URLs in sitemap")

        # filter URLs by keywords
        filtered_urls = self._filter_urls_by_keywords(urls=all_urls)
        logger.info(
            f"[{self._parser_name}] Filtered to {len(filtered_urls)} URLs "
            f"matching keywords: {self.KEYWORDS}"
        )

        if not filtered_urls:
            logger.warning(
                f"[{self._parser_name}] No URLs matched keywords, using base URL"
            )
            return [self._base_url]

        return filtered_urls

    async def parse_source(self, source: str) -> list[AllowanceDTO]:
        """
        Parse a Dom.rf page for allowances and normalize them.

        :param source: URL of the page to parse
        :return: list of allowances extracted from the page
        """

        logger.debug(f"[{self._parser_name}] Fetching page: {source}")

        async with self._create_client() as client:
            try:
                response = await client.get(source)
                logger.debug(
                    f"[{self._parser_name}] Page response: "
                    f"status={response.status_code}, size={len(response.content)} bytes"
                )

                if response.status_code != httpx.codes.OK:
                    logger.warning(
                        f"[{self._parser_name}] Page fetch failed with status "
                        f"{response.status_code}: {source}"
                    )
                    return []

                html = response.text

            except httpx.HTTPError as e:
                logger.error(f"[{self._parser_name}] HTTP error fetching page {source}: {e}")
                return []

        soup = BeautifulSoup(html, "html.parser")
        candidates = self._extract_candidates(soup=soup)
        logger.debug(f"[{self._parser_name}] Found {len(candidates)} candidate blocks")

        allowances: list[AllowanceDTO] = []

        for candidate in candidates:
            cleaned_name = self._normalize_text(value=candidate.get("name", ""))
            cleaned_number = self._normalize_npa(value=candidate.get("npa_number", ""))
            subjects = self._normalize_subjects(values=candidate.get("subjects", []))

            if cleaned_name and cleaned_number:
                allowances.append(
                    AllowanceDTO(
                        name=cleaned_name,
                        npa_number=cleaned_number,
                        subjects=subjects,
                    )
                )
                logger.debug(
                    f"[{self._parser_name}] Extracted allowance: "
                    f"name='{cleaned_name[:50]}...', npa='{cleaned_number}'"
                )
            else:
                logger.debug(
                    f"[{self._parser_name}] Skipped candidate: "
                    f"missing name or NPA number"
                )

        logger.info(
            f"[{self._parser_name}] Extracted {len(allowances)} valid allowances "
            f"from {source}"
        )

        return allowances

    def _extract_urls_from_sitemap(self, tree: etree.Element) -> list[str]:
        """
        Extract all URLs from a parsed sitemap XML.

        :param tree: parsed XML element tree
        :return: list of URLs found in the sitemap
        """

        urls: list[str] = []

        for element in tree.iter():
            if element.tag.endswith("loc") and element.text:
                urls.append(element.text.strip())

        return urls

    def _filter_urls_by_keywords(self, urls: list[str]) -> list[str]:
        """
        Filter URLs that contain any of the target keywords.

        :param urls: list of URLs to filter
        :return: filtered list of matching URLs
        """

        filtered: list[str] = []

        for url in urls:
            url_lower = url.lower()
            if any(keyword in url_lower for keyword in self.KEYWORDS):
                filtered.append(url)

        return filtered

    def _extract_candidates(
            self,
            soup: BeautifulSoup,
    ) -> list[dict[str, str | list[str]]]:
        """
        Extract raw allowance blocks from the parsed HTML.

        :param soup: parsed HTML document
        :return: list of dictionaries with raw fields
        """

        results: list[dict[str, str | list[str]]] = []

        # extract from headers
        headers = soup.find_all(["h1", "h2", "h3", "h4"])
        logger.debug(f"[{self._parser_name}] Found {len(headers)} headers to analyze")

        for header in headers:
            text = self._normalize_text(value=header.get_text(separator=" "))
            if not text:
                continue

            npa_number = self._find_npa_number(text=text)
            if npa_number:
                section_subjects = self._find_subjects(header=header)
                results.append({
                    "name": text,
                    "npa_number": npa_number,
                    "subjects": section_subjects,
                })

        # extract from law spans
        law_spans = soup.find_all("span", attrs={"data-law-number": True})
        logger.debug(f"[{self._parser_name}] Found {len(law_spans)} law spans to analyze")

        for span in law_spans:
            npa_number = self._normalize_npa(value=span.get("data-law-number", ""))
            name = self._normalize_text(value=span.get_text())
            if npa_number and name:
                results.append({
                    "name": name,
                    "npa_number": npa_number,
                    "subjects": [],
                })

        return results

    def _normalize_text(self, value: str) -> str:
        """
        Normalize free-form text by collapsing whitespace and trimming.

        :param value: raw text to normalize
        :return: cleaned text value
        """

        return " ".join(value.split()).strip()

    def _normalize_npa(self, value: str) -> str:
        """
        Normalize NPA number formatting by cleaning whitespace.

        :param value: raw NPA number
        :return: cleaned NPA number value
        """

        cleaned = self._normalize_text(value=value)
        cleaned = cleaned.replace("№", "№ ")
        cleaned = " ".join(cleaned.split())
        return cleaned

    def _normalize_subjects(self, values: list[str]) -> list[str] | None:
        """
        Normalize subject descriptors if present.

        :param values: raw list of subject strings
        :return: cleaned list of subjects or None
        """

        cleaned_values = [
            self._normalize_text(value=v)
            for v in values
            if self._normalize_text(value=v)
        ]
        return cleaned_values or None

    @staticmethod
    def _find_npa_number(text: str) -> str:
        """
        Find an NPA number pattern within text.

        :param text: text to search in
        :return: extracted NPA number or empty string
        """

        pattern = re.compile(r"№\s?[A-Za-zА-Яа-я0-9\-/]+")
        match = pattern.search(text)
        return match.group() if match else ""

    def _find_subjects(self, header) -> list[str]:
        """
        Infer subjects from sibling text near a header.

        :param header: BeautifulSoup header element
        :return: list of subject descriptors
        """

        subjects: list[str] = []

        for sibling in header.find_all_next(["p", "li"], limit=5):
            text = self._normalize_text(value=sibling.get_text())
            if text and len(text) < 240:
                subjects.append(text)

        return subjects
