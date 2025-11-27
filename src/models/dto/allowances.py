from pydantic import BaseModel, ConfigDict, Field


class AllowanceDTO(BaseModel):
    """
    External representation of an allowance payload.

    :return: allowance data ready for transport
    """

    id: int | None = Field(default=None)
    name: str = Field(...)
    npa_number: str = Field(...)
    subjects: list[str] | None = Field(default=None)

    model_config = ConfigDict(from_attributes=True)


class AllowanceCreateDTO(BaseModel):
    """
    Input payload for creating allowances.

    :return: validated allowance creation data
    """

    name: str = Field(...)
    npa_number: str = Field(...)
    subjects: list[str] | None = Field(default=None)
