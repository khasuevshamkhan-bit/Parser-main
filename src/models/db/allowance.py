from datetime import datetime

from sqlalchemy import DateTime, Integer, String, JSON
from sqlalchemy.orm import Mapped, mapped_column

from src.models.db.base import Base
from src.models.dto.allowances import AllowanceDTO


class Allowance(Base):
    """
    Database entity representing a social support allowance.
    """

    __tablename__ = "allowances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(length=512), nullable=False)
    npa_number: Mapped[str] = mapped_column(String(length=128), nullable=False)
    npa_name: Mapped[str | None] = mapped_column(String(length=512), nullable=True)
    subjects: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    def to_dto(self) -> AllowanceDTO:
        """
        Convert database model to DTO.

        :return: DTO representation of the allowance
        """

        return AllowanceDTO(
            id=self.id,
            name=self.name,
            npa_number=self.npa_number,
            npa_name=self.npa_name,
            subjects=self.subjects,
        )

    def __repr__(self) -> str:
        """
        Represent the allowance instance for debugging.

        :return: readable model representation
        """

        return f"Allowance(id={self.id}, name={self.name})"
