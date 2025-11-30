from pydantic import BaseModel, ConfigDict, Field


class AllowanceDTO(BaseModel):
    """
    External representation of an allowance payload.
    """

    id: int | None = Field(default=None)
    name: str = Field(...)
    npa_number: str = Field(...)
    npa_name: str | None = Field(default=None)
    level: str | None = Field(default=None, description="Federal or Regional")
    subjects: list[str] | None = Field(default=None)

    model_config = ConfigDict(from_attributes=True)


class AllowanceCreateDTO(BaseModel):
    """
    Input payload for creating allowances.
    """

    name: str = Field(...)
    npa_number: str = Field(...)
    npa_name: str | None = Field(default=None)
    level: str | None = Field(default=None)
    subjects: list[str] | None = Field(default=None)
