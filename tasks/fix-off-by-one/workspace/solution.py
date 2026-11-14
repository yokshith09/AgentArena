def sum_range(start, end):
    """Return the sum of all integers from start to end, both inclusive."""
    total = 0
    for n in range(start, end):
        total += n
    return total
