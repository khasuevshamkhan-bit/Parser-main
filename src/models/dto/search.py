from pydantic import BaseModel, Field


class InputFormDTO(BaseModel):
    """Incoming search payload."""

    input: str = Field(..., min_length=1, description="Free-form query to search for allowances")


class SearchResultDTO(BaseModel):
    """Vector search result item."""

    id: int = Field(..., description="Allowance identifier")
    name: str = Field(..., description="Allowance name")
    score: float = Field(..., ge=0, le=1, description="Similarity score between 0 and 1")
