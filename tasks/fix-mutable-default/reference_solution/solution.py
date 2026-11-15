def add_item(item, items=None):
    """Append item to items and return the list. Without `items`, start from a new empty list."""
    if items is None:
        items = []
    items.append(item)
    return items
