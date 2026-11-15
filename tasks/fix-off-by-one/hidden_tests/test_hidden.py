from solution import sum_range


def test_negative_to_positive():
    assert sum_range(-2, 2) == 0


def test_start_after_end_is_empty():
    assert sum_range(3, 2) == 0


def test_large_range():
    assert sum_range(1, 100) == 5050
