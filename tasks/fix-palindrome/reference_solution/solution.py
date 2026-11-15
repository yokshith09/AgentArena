def is_palindrome(text):
    """True if text reads the same forwards and backwards, ignoring case and non-alphanumerics."""
    cleaned = [c.lower() for c in text if c.isalnum()]
    return cleaned == cleaned[::-1]
