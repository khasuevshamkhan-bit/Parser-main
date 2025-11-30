from src.core.exceptions.allowances import AllowanceParsingError, AllowanceValidationError
from src.models.db.allowance import Allowance
from src.models.dto.allowances import AllowanceCreateDTO, AllowanceDTO
from src.parsers.base import BaseParser
from src.repositories.allowance_repository import AllowanceRepository


class AllowanceService:
    """
    Service layer orchestrating allowance workflows.

    :return: configured allowance service
    """

    def __init__(self, repository: AllowanceRepository) -> None:
        self._repository = repository

    async def list_allowances(self) -> list[AllowanceDTO]:
        """
        Fetch all allowances from storage.

        :return: collection of allowance schemas
        """

        allowances = await self._repository.list_all()

        return [allowance.to_dto() for allowance in allowances]

    async def create_allowance(self, payload: AllowanceCreateDTO) -> AllowanceDTO:
        """
        Create and persist an allowance from payload data.

        :return: saved allowance schema
        """

        name = self._clean_text(value=payload.name)
        npa_number = self._clean_text(value=payload.npa_number)
        subjects = self._normalize_subjects(subjects=payload.subjects)

        if not name or not npa_number:
            raise AllowanceValidationError("Allowance name and NPA number are required.")

        allowance = Allowance(
            name=name,
            npa_number=npa_number,
            subjects=subjects
        )

        saved = await self._repository.create(allowance=allowance)

        return saved.to_dto()

    async def parse_and_replace(self, parser: BaseParser) -> list[AllowanceDTO]:
        """
        Run parser and replace stored allowances with parsed results.

        :return: persisted parsed allowances
        """

        parsed = await parser.run()

        if not parsed:
            raise AllowanceParsingError

        allowances: list[Allowance] = []

        for item in parsed:
            name = self._clean_text(value=item.name)
            npa_number = self._clean_text(value=item.npa_number)
            subjects = self._normalize_subjects(subjects=item.subjects)

            if not name or not npa_number:
                raise AllowanceParsingError("Parsed allowance lacks required fields.")

            allowances.append(Allowance(name=name, npa_number=npa_number, subjects=subjects))

        models = await self._repository.replace_all(allowances=allowances)
        return [model.to_dto() for model in models]

    @staticmethod
    def _clean_text(value: str) -> str:
        """
        Normalize free-form text for persistence.

        :return: cleaned text value
        """

        return " ".join(value.split()).strip()

    def _normalize_subjects(self, subjects: list[str] | None) -> str | None:
        """
        Normalize subject collection into storage-friendly string.

        :return: comma-joined subjects or None
        """

        if not subjects:
            return None

        normalized = [self._clean_text(value=subject) for subject in subjects if self._clean_text(value=subject)]

        return ",".join(normalized) if normalized else None
