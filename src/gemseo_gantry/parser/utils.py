import keyword

from slugify import slugify


def sanitize_identifier(name: str) -> str:
    """Ensure a string is a valid Python identifier.

    Args:
        name: The candidate identifier string.

    Returns:
        A valid Python identifier derived from *name*.

    Raises:
        ValueError: If *name* is empty.
    """
    if not name:
        raise ValueError("Name cannot be empty")
    if name[0].isdigit():
        name = f"_{name}"
    if keyword.iskeyword(name):
        name = f"{name}_"
    return name


def pascalify(s: str) -> str:
    """Convert a string to PascalCase.

    Args:
        s (str): The input string.

    Returns:
        str: The PascalCase version of the input string.
    """
    slugified = slugify(s)
    components = slugified.split("-")
    pascal_case = "".join(x.title() for x in components)
    return pascal_case
