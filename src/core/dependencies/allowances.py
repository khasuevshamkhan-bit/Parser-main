from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.repositories.allowance_repository import AllowanceRepository
from src.services.allowance_service import AllowanceService


async def get_allowance_repository(session: AsyncSession = Depends(get_session)) -> AllowanceRepository:
    """
    Provide allowance repository bound to a session.

    :return: allowance repository instance
    """

    return AllowanceRepository(session=session)


async def get_allowance_service(
        repository: AllowanceRepository = Depends(get_allowance_repository)) -> AllowanceService:
    """
    Provide allowance service wired with repository.

    :return: configured allowance service
    """

    return AllowanceService(repository=repository)
