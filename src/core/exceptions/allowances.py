from fastapi.exceptions import HTTPException

"""
Allowance domain exceptions aligned with HTTP semantics.

:return: module defining allowance-related HTTP exceptions
"""


class AllowanceError(HTTPException):
    """
    Base class for allowance exceptions exposed over HTTP.

    :return: initialized HTTP exception
    """


class AllowanceValidationError(AllowanceError):
    """
    Raised when allowance payloads fail validation rules.

    :return: HTTP 400 exception for validation errors
    """

    def __init__(self, detail: str = "Invalid allowance data.") -> None:
        super().__init__(status_code=400, detail=detail)


class AllowanceParsingError(AllowanceError):
    """
    Raised when external parsing fails to produce valid allowances.

    :return: HTTP 502 exception for parsing failures
    """

    def __init__(self, detail: str = "Failed to parse allowances from source.") -> None:
        super().__init__(status_code=502, detail=detail)
