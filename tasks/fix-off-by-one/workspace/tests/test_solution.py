from solution import sum_range


def test_small_range():
    assert sum_range(1, 4) == 10


def test_single_value():
    assert sum_range(5, 5) == 5
