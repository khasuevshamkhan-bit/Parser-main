from sqlalchemy import delete, select
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

    async def replace_all(self, allowances: list[Allowance]) -> list[Allowance]:
        """
        Replace all stored allowances with provided collection.

        :return: saved allowance rows
        """

        await self._session.execute(delete(Allowance))
        self._session.add_all(allowances)
        await self._session.commit()
        for allowance in allowances:
            await self._session.refresh(allowance)
        return allowances
