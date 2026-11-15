from solution import is_palindrome


def test_not_a_palindrome():
    assert not is_palindrome("hello")


def test_empty_string():
    assert is_palindrome("")


def test_digits():
    assert is_palindrome("12321")
    assert not is_palindrome("12345")


def test_more_phrases():
    assert is_palindrome("No lemon, no melon")
    assert is_palindrome("Was it a car or a cat I saw?")
