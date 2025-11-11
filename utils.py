def not_none[T](value: T | None, value_name: str | None = None) -> T:
    value_name_str = f" '{value_name}'" if value_name else ""
    if value is None:
        raise ValueError(f"Value{value_name_str} is None, which is unexpected")
    return value
