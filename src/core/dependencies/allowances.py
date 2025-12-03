from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.dependencies.vector_search import get_allowance_embedding_service
from src.repositories.allowance_repository import AllowanceRepository
from src.services.allowance_embedding_service import AllowanceEmbeddingService
from src.services.allowance_service import AllowanceService


async def get_allowance_repository(session: AsyncSession = Depends(get_session)) -> AllowanceRepository:
    """
    Provide allowance repository bound to the current session.
    """

    return AllowanceRepository(session=session)


async def get_allowance_service(
        repository: AllowanceRepository = Depends(get_allowance_repository),
) -> AllowanceService:
    """
    Provide allowance service without embedding dependencies.
    """

    return AllowanceService(repository=repository, embedding_service=None)


async def get_allowance_service_with_embeddings(
        repository: AllowanceRepository = Depends(get_allowance_repository),
        embedding_service: AllowanceEmbeddingService = Depends(get_allowance_embedding_service),
) -> AllowanceService:
    """
    Provide allowance service with embedding support enabled.
    """

    return AllowanceService(repository=repository, embedding_service=embedding_service)
