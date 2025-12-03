class TextNormalizer:
    """
    Lightweight normalizer for free-form text.
    """

    def normalize(self, value: str | None) -> str:
        """
        Collapse whitespace and trim surrounding spaces.
        """

        if not value:
            return ""
        return " ".join(value.split()).strip()


class AllowanceEmbeddingBuilder:
    """
    Compose textual representations of allowances for embedding.
    """

    def __init__(self, normalizer: TextNormalizer | None = None) -> None:
        self._normalizer = normalizer or TextNormalizer()

    def build_document(self, name: str, npa_name: str, level: str | None, subjects: list[str] | None,
                       validity_period: str | None) -> str:
        """
        Combine allowance attributes into a single passage string.
        """

        parts: list[str] = []
        cleaned_name = self._normalizer.normalize(value=name)
        cleaned_npa = self._normalizer.normalize(value=npa_name)
        cleaned_level = self._normalizer.normalize(value=level)
        cleaned_validity = self._normalizer.normalize(value=validity_period)

        if cleaned_name:
            parts.append(f"name: {cleaned_name}")
        if cleaned_level:
            parts.append(f"level: {cleaned_level}")
        if cleaned_npa:
            parts.append(f"legal_basis: {cleaned_npa}")
        if subjects:
            cleaned_subjects = [self._normalizer.normalize(value=subject) for subject in subjects if subject]
            if cleaned_subjects:
                parts.append(f"eligibility: {'; '.join(cleaned_subjects)}")
        if cleaned_validity:
            parts.append(f"validity: {cleaned_validity}")

        passage = " | ".join(part for part in parts if part)
        if not passage:
            return ""
        return f"passage: {passage}"


class QueryEmbeddingBuilder:
    """
    Prepare questionnaire text for embedding queries.
    """

    def __init__(self, normalizer: TextNormalizer | None = None) -> None:
        self._normalizer = normalizer or TextNormalizer()

    def build_query(self, user_input: str) -> str:
        """
        Normalize and prefix user input according to embedding model expectations.
        """

        cleaned = self._normalizer.normalize(value=user_input)
        if not cleaned:
            return ""
        return f"query: {cleaned}"
