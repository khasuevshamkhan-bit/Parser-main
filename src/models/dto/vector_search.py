from pydantic import BaseModel, Field, field_validator


class InputFormDTO(BaseModel):
    """
    Questionnaire payload containing free-form user input.
    """

    input: str = Field(..., description="Concatenated answers from the user questionnaire")

    @field_validator('input', mode='after')
    @classmethod
    def validate_input(cls, value: str) -> str:
        str_lentgth = len(value)
        if str_lentgth < 2:
            raise ValueError(f'User input is too short: {str_lentgth}')

        return value


class VectorDTO(BaseModel):
    """
    Dense vector representation of a textual payload.
    """

    embedding: list[float] = Field(..., description="Normalized embedding vector")


class AllowanceVectorizeRequestDTO(BaseModel):
    """
    Identifiers of allowances that should receive embeddings.
    """

    allowance_ids: list[int] = Field(..., description="Allowance identifiers to vectorize")


class AllowanceVectorizeResultDTO(BaseModel):
    """
    Report about allowance embedding creation results.
    """

    processed_ids: list[int] = Field(..., description="Allowance ids that now have embeddings")
    missing_ids: list[int] = Field(..., description="Allowance ids not found in storage")


class VectorSearchResultDTO(BaseModel):
    """
    Response item returned by the vector search endpoint.
    """

    allowance_id: int = Field(..., description="Identifier of the matched allowance")
    allowance_name: str = Field(..., description="Title of the matched allowance")
    score: float = Field(..., description="Similarity score where higher means closer match")
