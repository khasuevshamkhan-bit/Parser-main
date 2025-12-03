from pydantic import BaseModel, Field


class InputFormDTO(BaseModel):
    """
    Questionnaire payload containing free-form user input.
    """

    input: str = Field(..., description="Concatenated answers from the user questionnaire")


class VectorSearchResultDTO(BaseModel):
    """
    Response item returned by the vector search endpoint.
    """

    allowance_id: int = Field(..., description="Identifier of the matched allowance")
    allowance_name: str = Field(..., description="Title of the matched allowance")
    score: float = Field(..., description="Similarity score where lower means closer match")
