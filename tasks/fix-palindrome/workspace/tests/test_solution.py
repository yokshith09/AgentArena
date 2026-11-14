from solution import is_palindrome


def test_plain_palindrome():
    assert is_palindrome("level")


def test_phrase_with_punctuation():
    assert is_palindrome("A man, a plan, a canal: Panama")
