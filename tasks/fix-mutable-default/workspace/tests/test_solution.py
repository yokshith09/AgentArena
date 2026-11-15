from solution import add_item


def test_first_call():
    assert add_item(1) == [1]


def test_calls_do_not_share_state():
    assert add_item(2) == [2]
