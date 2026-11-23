from dataguard.catalog import Catalog
from dataguard.matching import match_category


def make_catalog():
    return Catalog(
        categories=frozenset({"adhesivos", "condimentos", "cemento", "cementos", "papel", "limpieza"}),
        aliases={
            "adhesivos": "adhesivos",
            "adesivos": "adhesivos",
            "adhesivo": "adhesivos",
            "condimentos": "condimentos",
            "condim": "condimentos",
            "condimento": "condimentos",
            "cemento": "cemento",
            "cementos": "cementos",
            "papel": "papel",
            "papeleria": "papel",
            "limpieza": "limpieza",
        },
        display_names={
            "adhesivos": "Adhesivos",
            "condimentos": "Condimentos",
            "cemento": "Cemento",
            "cementos": "Cementos",
            "papel": "Papel",
            "limpieza": "Limpieza",
        },
    )


def test_exact_match_after_normalization():
    result = match_category("  ADHESIVOS ", make_catalog())
    assert result.kind == "exact"
    assert result.canonical == "adhesivos"


def test_alias_match_is_approved_not_fuzzy():
    result = match_category("adesivos", make_catalog())
    assert result.kind == "alias"
    assert result.canonical == "adhesivos"


def test_fuzzy_match_is_suggested_when_clear_winner():
    result = match_category("condimntos", make_catalog())
    assert result.kind == "fuzzy"
    assert result.canonical == "condimentos"
    assert result.score is not None and result.score >= 90


def test_ambiguous_match_has_no_correction():
    result = match_category("cemeto", make_catalog())
    assert result.kind == "ambiguous"
    assert result.canonical is None
    assert len(result.candidates) >= 2


def test_no_match_is_rejected():
    result = match_category("Maquinaria", make_catalog())
    assert result.kind == "no_match"
    assert result.canonical is None
