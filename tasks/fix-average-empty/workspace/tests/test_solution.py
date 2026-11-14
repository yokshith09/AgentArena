from solution import average


def test_average_of_two():
    assert average([2, 4]) == 3


def test_empty_list_is_zero():
    assert average([]) == 0.0
