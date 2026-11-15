from solution import average


def test_single_value():
    assert average([7]) == 7


def test_float_result():
    assert average([1, 2, 3, 4]) == 2.5


def test_negative_values():
    assert average([-1, 1]) == 0


def test_empty_returns_float():
    assert isinstance(average([]), float)
