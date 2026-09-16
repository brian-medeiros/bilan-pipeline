import pytest

from bilan_pipeline.geometry import polygon_to_norm, same_row, union
from bilan_pipeline.parsing import parse_number


@pytest.mark.parametrize(
    "text,expected",
    [
        ("1 234", 1234),
        ("1\u00a0234,50", 1234.5),
        ("1\u202f234", 1234),
        ("(2 340)", -2340),
        ("- 12", -12),
        ("1.234.567", 1234567),
        ("1.234,56", 1234.56),
        ("0", 0),
        ("0,00", 0),
        ("", None),
        ("-", None),
        ("—", None),
        ("1 234\n567", 1234567),
        ("FY2023", None),
        ("O12", None),
        ("12 EUR", 12),
        ("−3", -3),
    ],
)
def test_french_number(text, expected):
    assert parse_number(text) == expected


def test_normalization_and_union():
    assert polygon_to_norm([[0, 0], [1250, 0], [1250, 1750], [0, 1750]], 600, 840) == [
        0,
        0,
        0.5,
        0.5,
    ]
    assert union([[0.1, 0.2, 0.3, 0.4], [0.2, 0.3, 0.8, 0.9]]) == [0.1, 0.2, 0.8, 0.9]


def test_invalid_geometry_is_rejected():
    with pytest.raises(ValueError):
        polygon_to_norm([[0, 0], [10000, 10000]], 600, 840)
    with pytest.raises(ValueError):
        union([])


def test_row_alignment():
    assert same_row([0.1, 0.10, 0.4, 0.12], [0.7, 0.105, 0.8, 0.125])
    assert not same_row([0.1, 0.10, 0.4, 0.12], [0.7, 0.14, 0.8, 0.16])
