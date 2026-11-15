import re


def slugify(text):
    """Return a URL slug: lowercase, runs of non-alphanumerics become one hyphen, no edge hyphens."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
