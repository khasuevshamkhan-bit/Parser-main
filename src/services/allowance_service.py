from src.core.exceptions.allowances import AllowanceParsingError, AllowanceValidationError
from src.models.db.allowance import Allowance
from src.models.dto.allowances import AllowanceCreateDTO, AllowanceDTO
from src.parsers.base import BaseSeleniumParser
from src.repositories.allowance_repository import AllowanceRepository
from src.services.allowance_embedding_service import AllowanceEmbeddingService
from src.utils.logger import logger


class AllowanceService:
    """
    Service layer orchestrating allowance workflows.

    Handles business logic for listing, creating, and parsing allowances.
    """

    def __init__(
            self,
            repository: AllowanceRepository,
            embedding_service: AllowanceEmbeddingService | None = None,
    ) -> None:
        """
        Initialize the allowance service with persistence and indexing tools.
        """

        self._repository = repository
        self._embedding_service = embedding_service

    async def list_allowances(self) -> list[AllowanceDTO]:
        """
        Fetch all allowances from storage.
        """

        logger.debug("Fetching all allowances from storage")
        allowances = await self._repository.list_all()
        logger.info(f"Retrieved {len(allowances)} allowances from storage")

        return [allowance.to_dto() for allowance in allowances]

    async def create_allowance(self, payload: AllowanceCreateDTO) -> AllowanceDTO:
        """
        Create and persist an allowance from payload data.
        """

        logger.debug(f"Creating allowance: name='{payload.name[:50]}...'")

        name = self._clean_text(value=payload.name)
        npa_name = self._clean_text(value=payload.npa_name) if payload.npa_name else None
        level = self._clean_text(value=payload.level) if payload.level else None
        subjects = self._normalize_subjects(subjects=payload.subjects)
        validity_period = (
            self._clean_text(value=payload.validity_period)
            if payload.validity_period
            else None
        )

        if not name or not npa_name:
            logger.error("Allowance creation failed: missing name or NPA text")
            raise AllowanceValidationError("Allowance name and NPA description are required.")

        allowance = Allowance(
            name=name,
            npa_name=npa_name,
            level=level,
            subjects=subjects,
            validity_period=validity_period,
        )

        saved = await self._repository.create(allowance=allowance)
        logger.info(f"Created allowance with id={saved.id}")

        if self._embedding_service:
            await self._embedding_service.index_allowance(allowance=saved)

        return saved.to_dto()

    async def parse_and_replace(self, parser: BaseSeleniumParser) -> list[AllowanceDTO]:
        """
        Run parser and persist only new allowances based on NPA names.
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
        duplicate_parsed = 0
        seen_npa_names: set[str] = set()

        for idx, item in enumerate(parsed):
            name = self._clean_text(value=item.name)
            npa_name = self._clean_text(value=item.npa_name) if item.npa_name else None
            level = self._clean_text(value=item.level) if item.level else None
            subjects = self._normalize_subjects(subjects=item.subjects)
            validity_period = (
                self._clean_text(value=item.validity_period)
                if item.validity_period
                else None
            )

            if not name or not npa_name:
                skipped_count += 1
                logger.warning(
                    f"Skipping parsed item {idx + 1}: missing required fields "
                    f"(name='{name[:30] if name else 'empty'}...', npa='{npa_name}')"
                )
                continue

            if npa_name in seen_npa_names:
                duplicate_parsed += 1
                logger.info(
                    f"Skipping duplicate parsed item {idx + 1} with NPA='{npa_name}'"
                )
                continue

            seen_npa_names.add(npa_name)

            allowances.append(
                Allowance(
                    name=name,
                    npa_name=npa_name,
                    level=level,
                    subjects=subjects,
                    validity_period=validity_period,
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
            f"(skipped {skipped_count} invalid, duplicates in payload={duplicate_parsed})"
        )

        existing_npa_names = await self._repository.get_existing_npa_names(
            npa_names=list(seen_npa_names)
        )

        new_allowances = [
            allowance
            for allowance in allowances
            if allowance.npa_name not in existing_npa_names
        ]

        if not new_allowances:
            logger.warning(
                "No new allowances to save: all parsed NPAs already exist in storage."
            )
            return []

        models = await self._repository.bulk_create(allowances=new_allowances)
        logger.info(
            f"Stored {len(models)} new allowances "
            f"(skipped existing in DB={len(existing_npa_names)})"
        )

        if self._embedding_service:
            await self._embedding_service.index_many(allowances=models)

        return [model.to_dto() for model in models]

    @staticmethod
    def _clean_text(value: str) -> str:
        """
        Normalize free-form text for persistence.
        """

        return " ".join(value.split()).strip()

    def _normalize_subjects(self, subjects: list[str] | None) -> list[str] | None:
        """
        Normalize subject collection.
        """

        if not subjects:
            return None

        normalized = [
            self._clean_text(value=subject)
            for subject in subjects
            if self._clean_text(value=subject)
        ]

        return normalized if normalized else None
