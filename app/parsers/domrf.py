import asyncio
import re
import xml.etree.ElementTree as etree

from bs4 import BeautifulSoup
import httpx

from app.dto import AllowanceDTO
from app.parsers.base import BaseParser


class DomRfParser(BaseParser):
    """
    Parser tailored for extracting allowance data from Dom.rf pages.

    :return: initialized Dom.rf parser
    """

    def __init__(self, root_url: str = "https://xn--80az8a.xn--p1ai") -> None:
        super().__init__()
        self.root_url = root_url.rstrip("/")
        self.keywords = ["поддерж", "субсид", "пособ", "ипотек", "льгот"]

    async def fetch_sources(self) -> list[str]:
        """
        Discover candidate Dom.rf URLs containing social support information.

        :return: filtered list of URLs to parse
        """

        sitemap_url = f"{self.root_url}/sitemap.xml"
        async with self._client() as client:
            response = await client.get(sitemap_url)
            if response.status_code != httpx.codes.OK:
                return [self.root_url]
            tree = etree.fromstring(response.content)
        urls = [element.text for element in tree.iter() if element.tag.endswith("loc") and element.text]
        filtered = []
        for url in urls:
            if any(keyword in url.lower() for keyword in self.keywords):
                filtered.append(url)
        if not filtered:
            filtered.append(self.root_url)
        return filtered

    async def parse_source(self, source: str) -> list[AllowanceDTO]:
        """
        Parse a Dom.rf page for allowances and normalize them.

        :return: list of allowances extracted from the page
        """

        async with self._client() as client:
            response = await client.get(source)
            if response.status_code != httpx.codes.OK:
                return []
            html = response.text
        soup = BeautifulSoup(html, "html.parser")
        candidates = self._extract_candidates(soup)
        allowances: list[AllowanceDTO] = []
        for candidate in candidates:
            cleaned_name = self._normalize_text(candidate.get("name", ""))
            cleaned_number = self._normalize_npa(candidate.get("npa_number", ""))
            subjects = self._normalize_subjects(candidate.get("subjects", []))
            if cleaned_name and cleaned_number:
                allowances.append(
                    AllowanceDTO(
                        name=cleaned_name,
                        npa_number=cleaned_number,
                        subjects=subjects,
                    )
                )
        return allowances

    def _extract_candidates(self, soup: BeautifulSoup) -> list[dict[str, str | list[str]]]:
        """
        Extract raw allowance blocks from the parsed HTML.

        :return: list of dictionaries with raw fields
        """

        results: list[dict[str, str | list[str]]] = []
        headers = soup.find_all(["h1", "h2", "h3", "h4"])
        for header in headers:
            text = self._normalize_text(header.get_text(separator=" "))
            if not text:
                continue
            npa_number = self._find_npa_number(text)
            section_subjects = self._find_subjects(header)
            if npa_number:
                results.append({"name": text, "npa_number": npa_number, "subjects": section_subjects})
        law_spans = soup.find_all("span", attrs={"data-law-number": True})
        for span in law_spans:
            npa_number = self._normalize_npa(span.get("data-law-number", ""))
            name = self._normalize_text(span.get_text())
            if npa_number and name:
                results.append({"name": name, "npa_number": npa_number, "subjects": []})
        return results

    def _normalize_text(self, value: str) -> str:
        """
        Normalize free-form text by collapsing whitespace and trimming.

        :return: cleaned text value
        """

        return " ".join(value.split()).strip()

    def _normalize_npa(self, value: str) -> str:
        """
        Normalize NPA number formatting by removing redundant characters.

        :return: cleaned NPA number value
        """

        cleaned = self._normalize_text(value)
        cleaned = cleaned.replace("№", "№ ")
        cleaned = " ".join(cleaned.split())
        return cleaned

    def _normalize_subjects(self, values: list[str]) -> list[str] | None:
        """
        Normalize subject descriptors if present.

        :return: cleaned list of subjects or None
        """

        cleaned_values = [self._normalize_text(value) for value in values if self._normalize_text(value)]
        return cleaned_values or None

    def _find_npa_number(self, text: str) -> str:
        """
        Find an NPA number pattern within text.

        :return: extracted NPA number or empty string
        """

        pattern = re.compile(r"№\s?[A-Za-zА-Яа-я0-9\-/]+")
        match = pattern.search(text)
        if match:
            return match.group()
        return ""

    def _find_subjects(self, header) -> list[str]:
        """
        Infer subjects from sibling text near a header.

        :return: list of subject descriptors
        """

        subjects: list[str] = []
        for sibling in header.find_all_next(["p", "li"], limit=5):
            text = self._normalize_text(sibling.get_text())
            if text and len(text) < 240:
                subjects.append(text)
        return subjects
