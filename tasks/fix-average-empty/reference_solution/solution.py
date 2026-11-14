def average(values):
    """Arithmetic mean of a list of numbers; 0.0 for an empty list."""
    if not values:
        return 0.0
    return sum(values) / len(values)
