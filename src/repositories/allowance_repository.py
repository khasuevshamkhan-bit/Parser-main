from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.db.allowance import Allowance


class AllowanceRepository:
    """
    Repository layer for allowance persistence.

    :return: repository instance bound to a database session
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[Allowance]:
        """
        Retrieve all allowances ordered by creation time.

        :return: list of allowance rows
        """

        statement = select(Allowance).order_by(Allowance.created_at.desc())
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def create(self, allowance: Allowance) -> Allowance:
        """
        Persist a single allowance entity.

        :return: saved allowance row
        """

        self._session.add(allowance)
        await self._session.commit()
        await self._session.refresh(allowance)
        return allowance

    async def get_existing_npa_names(self, npa_names: list[str]) -> set[str]:
        """
        Fetch NPA names that are already stored.

        :param npa_names: list of NPA names to check
        :return: set of NPA names present in storage
        """

        if not npa_names:
            return set()

        statement = select(Allowance.npa_name).where(Allowance.npa_name.in_(npa_names))
        result = await self._session.execute(statement)
        return set(result.scalars().all())

    async def bulk_create(self, allowances: list[Allowance]) -> list[Allowance]:
        """
        Persist a batch of allowance entities.

        :param allowances: allowances to save
        :return: saved allowance rows
        """

        if not allowances:
            return []

        self._session.add_all(allowances)
        await self._session.commit()
        for allowance in allowances:
            await self._session.refresh(allowance)
        return allowances
