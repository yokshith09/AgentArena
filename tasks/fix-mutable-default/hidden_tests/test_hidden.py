from solution import add_item


def test_explicit_list_is_extended():
    assert add_item("a", ["x"]) == ["x", "a"]


def test_explicit_list_is_mutated_in_place():
    lst = []
    add_item(1, lst)
    assert lst == [1]


def test_repeated_default_calls_are_independent():
    assert add_item("a") == ["a"]
    assert add_item("b") == ["b"]
    assert add_item("c") == ["c"]
