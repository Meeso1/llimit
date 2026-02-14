from typing import Any


class AdditionalDataValidationError(ValueError):
    """Raised when additional_data contains invalid values"""
    pass


def validate_additional_data(additional_data: dict[str, Any], content_type: str) -> None:
    """
    Validate additional_data fields used in pricing calculations.
    
    Raises:
        AdditionalDataValidationError: If validation fails
    """
    if not additional_data:
        return
    
    numeric_fields = [
        "page_count",
        "text_token_count", 
        "estimated_native_token_count",
        "token_count",
        "length_seconds",
    ]

    for field in numeric_fields:
        if field in additional_data:
            value = additional_data[field]
            if not isinstance(value, (int, float)):
                raise AdditionalDataValidationError(
                    f"Field '{field}' must be a number, got {type(value).__name__}"
                )
            if value < 0:
                raise AdditionalDataValidationError(
                    f"Field '{field}' must be non-negative, got {value}"
                )

    bool_fields = [
        "has_selectable_text",
    ]

    for field in bool_fields:
        if field in additional_data:
            value = additional_data[field]
            if not isinstance(value, bool):
                raise AdditionalDataValidationError(
                    f"Field '{field}' must be a boolean, got {type(value).__name__}"
                )
