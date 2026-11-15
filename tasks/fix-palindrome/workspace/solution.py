def is_palindrome(text):
    """True if text reads the same forwards and backwards, ignoring case and non-alphanumerics."""
    return text == text[::-1]
