from src.core.exceptions.allowances import AllowanceParsingError, AllowanceValidationError
from src.models.db.allowance import Allowance
from src.models.dto.allowances import AllowanceCreateDTO, AllowanceDTO
from src.parsers.base import BaseSeleniumParser
from src.repositories.allowance_repository import AllowanceRepository
from src.utils.logger import logger


class AllowanceService:
    """
    Service layer orchestrating allowance workflows.

    Handles business logic for listing, creating, and parsing allowances.
    """

    def __init__(self, repository: AllowanceRepository) -> None:
        """
        Initialize the allowance service.

        :param repository: repository for allowance persistence
        """

        self._repository = repository

    async def list_allowances(self) -> list[AllowanceDTO]:
        """
        Fetch all allowances from storage.

        :return: collection of allowance schemas
        """

        logger.debug("Fetching all allowances from storage")
        allowances = await self._repository.list_all()
        logger.info(f"Retrieved {len(allowances)} allowances from storage")

        return [allowance.to_dto() for allowance in allowances]

    async def create_allowance(self, payload: AllowanceCreateDTO) -> AllowanceDTO:
        """
        Create and persist an allowance from payload data.

        :param payload: allowance creation data
        :return: saved allowance schema
        """

        logger.debug(f"Creating allowance: name='{payload.name[:50]}...'")

        name = self._clean_text(value=payload.name)
        npa_number = self._clean_text(value=payload.npa_number)
        subjects = self._normalize_subjects(subjects=payload.subjects)

        if not name or not npa_number:
            logger.error("Allowance creation failed: missing name or NPA number")
            raise AllowanceValidationError("Allowance name and NPA number are required.")

        allowance = Allowance(
            name=name,
            npa_number=npa_number,
            subjects=subjects,
        )

        saved = await self._repository.create(allowance=allowance)
        logger.info(f"Created allowance with id={saved.id}")

        return saved.to_dto()

    async def parse_and_replace(self, parser: BaseSeleniumParser) -> list[AllowanceDTO]:
        """
        Run parser and replace stored allowances with parsed results.

        :param parser: Selenium parser instance to execute
        :return: persisted parsed allowances
        """

        parser_name = parser.__class__.__name__
        logger.info(f"Starting parse_and_replace with {parser_name}")

        try:
            parsed = await parser.run_async()
        except Exception as e:
            logger.error(f"Parser {parser_name} raised exception: {e}")
            raise AllowanceParsingError(detail=f"Parser failed with error: {e}")

        if not parsed:
            logger.error(f"Parser {parser_name} returned no allowances")
            raise AllowanceParsingError(
                detail="Parser returned empty result. Check logs for details."
            )

        logger.info(f"Parser {parser_name} returned {len(parsed)} raw allowances")

        allowances: list[Allowance] = []
        skipped_count = 0

        for idx, item in enumerate(parsed):
            name = self._clean_text(value=item.name)
            npa_number = self._clean_text(value=item.npa_number)
            subjects = self._normalize_subjects(subjects=item.subjects)

            if not name or not npa_number:
                skipped_count += 1
                logger.warning(
                    f"Skipping parsed item {idx + 1}: missing required fields "
                    f"(name='{name[:30] if name else 'empty'}...', npa='{npa_number}')"
                )
                continue

            allowances.append(
                Allowance(
                    name=name,
                    npa_number=npa_number,
                    subjects=subjects,
                )
            )

        if not allowances:
            logger.error(
                f"All {len(parsed)} parsed items were invalid "
                f"(skipped={skipped_count})"
            )
            raise AllowanceParsingError(
                detail="All parsed allowances lacked required fields."
            )

        logger.info(
            f"Prepared {len(allowances)} valid allowances for storage "
            f"(skipped {skipped_count} invalid)"
        )

        models = await self._repository.replace_all(allowances=allowances)
        logger.info(f"Replaced storage with {len(models)} allowances")

        return [model.to_dto() for model in models]

    @staticmethod
    def _clean_text(value: str) -> str:
        """
        Normalize free-form text for persistence.

        :param value: raw text to clean
        :return: cleaned text value
        """

        return " ".join(value.split()).strip()

    def _normalize_subjects(self, subjects: list[str] | None) -> str | None:
        """
        Normalize subject collection into storage-friendly string.

        :param subjects: list of subject strings or None
        :return: comma-joined subjects or None
        """

        if not subjects:
            return None

        normalized = [
            self._clean_text(value=subject)
            for subject in subjects
            if self._clean_text(value=subject)
        ]

        return ",".join(normalized) if normalized else None
