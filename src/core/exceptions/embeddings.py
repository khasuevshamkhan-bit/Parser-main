from fastapi.exceptions import HTTPException

"""
Custom HTTP exceptions for embedding workflows.
"""


class EmbeddingError(HTTPException):
    """
    Base class for embedding-related HTTP errors.
    """


class EmbeddingValidationError(EmbeddingError):
    """
    Raised when embedding requests fail validation rules.
    """

    def __init__(self, detail: str = "Embedding request is invalid.") -> None:
        super().__init__(status_code=400, detail=detail)


class EmbeddingNotFoundError(EmbeddingError):
    """
    Raised when referenced resources for embedding are missing.
    """

    def __init__(self, detail: str = "Referenced resources were not found.") -> None:
        super().__init__(status_code=404, detail=detail)


class EmbeddingProcessingError(EmbeddingError):
    """
    Raised when the embedding pipeline cannot complete successfully.
    """

    def __init__(self, detail: str = "Embedding processing failed.") -> None:
        super().__init__(status_code=500, detail=detail)
