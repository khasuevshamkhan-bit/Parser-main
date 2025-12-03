from pydantic import BaseModel, Field


class InputFormDTO(BaseModel):
    """
    Questionnaire payload containing free-form user input.
    """

    input: str = Field(..., description="Concatenated answers from the user questionnaire")


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
    score: float = Field(..., description="Similarity score where lower means closer match")
