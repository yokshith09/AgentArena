from solution import slugify


def test_punctuation():
    assert slugify("Hello, World!") == "hello-world"


def test_repeated_separators():
    assert slugify("a--b__c") == "a-b-c"


def test_empty_and_symbols_only():
    assert slugify("") == ""
    assert slugify("!!!") == ""


def test_digits_are_kept():
    assert slugify("Python 3.12 Release") == "python-3-12-release"
