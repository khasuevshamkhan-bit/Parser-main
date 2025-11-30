from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.db.base import Base
from src.models.dto.allowances import AllowanceDTO


class Allowance(Base):
    """
    Database entity representing a social support allowance.

    :return: persisted allowance row
    """

    __tablename__ = "allowances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(length=512), nullable=False)
    npa_number: Mapped[str] = mapped_column(String(length=128), nullable=False)
    subjects: Mapped[str | None] = mapped_column(String(length=1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    def to_dto(self) -> AllowanceDTO:
        return AllowanceDTO.model_validate(self)

    def __repr__(self) -> str:
        """
        Represent the allowance instance for debugging.

        :return: readable model representation
        """

        return f"Allowance(id={self.id}, name={self.name})"
