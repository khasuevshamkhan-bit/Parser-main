from pydantic import BaseModel
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):

    def to_dto(self) -> BaseModel:
        """
        Converts a database model into a BaseModel DTO object.
        """
        pass
