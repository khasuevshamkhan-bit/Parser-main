from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.config import settings
from src.models.db.allowance import Allowance
from src.models.db.base import Base


class AllowanceEmbedding(Base):
    """
    Vector representation of an allowance for semantic search.
    """

    __tablename__ = "allowance_embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    allowance_id: Mapped[int] = mapped_column(
        ForeignKey("allowances.id"),
        nullable=False,
        unique=True,
    )
    embedding_model: Mapped[str] = mapped_column(String(length=128), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(dim=settings.vector.dimension),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    allowance: Mapped[Allowance] = relationship(
        argument=Allowance,
        back_populates="embedding",
    )
