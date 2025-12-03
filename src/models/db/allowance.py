from datetime import datetime

from sqlalchemy import DateTime, Integer, String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.db.base import Base
from src.models.dto.allowances import AllowanceDTO


class Allowance(Base):
    """
    Database entity representing a social support allowance.
    """

    __tablename__ = "allowances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(length=512), nullable=False)
    npa_name: Mapped[str] = mapped_column(String(length=512), nullable=False)
    level: Mapped[str | None] = mapped_column(String(length=64), nullable=True)
    subjects: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    validity_period: Mapped[str | None] = mapped_column(String(length=128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    embedding = relationship(
        argument="AllowanceEmbedding",
        back_populates="allowance",
        uselist=False,
    )

    def to_dto(self) -> AllowanceDTO:
        """
        Convert database model to DTO.

        :return: DTO representation of the allowance
        """

        return AllowanceDTO(
            id=self.id,
            name=self.name,
            npa_name=self.npa_name,
            level=self.level,
            subjects=self.subjects,
            validity_period=self.validity_period,
        )

    def __repr__(self) -> str:
        """
        Represent the allowance instance for debugging.

        :return: readable model representation
        """

        return f"Allowance(id={self.id}, name={self.name})"
