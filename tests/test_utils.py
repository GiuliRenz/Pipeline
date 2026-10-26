import pytest

from src.utils import slugify


@pytest.mark.parametrize(
    ("city", "expected"),
    [
        ("Bahía Blanca", "bahia_blanca"),
        ("Bahia Blanca", "bahia_blanca"),
        ("Córdoba", "cordoba"),
        ("  Buenos   Aires ", "buenos_aires"),
    ],
)
def test_slugify(city, expected):
    assert slugify(city) == expected
