def validate_coordinates(value: list[float]) -> list[float]:
    if len(value) != 3 or not all(-1000 <= coordinate <= 1000 for coordinate in value):
        raise ValueError("Expected three coordinates within [-1000, 1000]")
    return value
