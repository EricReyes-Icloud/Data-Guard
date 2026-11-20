import pytest
from hypothesis import given, strategies as st

from dataguard.normalization import hygiene_trace, normalize


def test_display_profile_keeps_case_and_accents():
    assert normalize("  Café  ", "display") == "Café"


def test_match_profile_is_aggressive():
    assert normalize("  Café  ", "match") == "cafe"


@pytest.mark.parametrize("placeholder", ["N/A", "n/a", "-", " n/a "])
def test_placeholders_become_empty_in_both_profiles(placeholder):
    assert normalize(placeholder, "display") == ""
    assert normalize(placeholder, "match") == ""


def test_punctuation_is_removed_only_in_match_profile():
    assert normalize("Condim.", "display") == "Condim."
    assert normalize("Condim.", "match") == "condim"


def test_whitespace_is_collapsed():
    assert normalize("PEGAMENTO   BLANCO", "display") == "PEGAMENTO BLANCO"
    assert normalize("PEGAMENTO   BLANCO", "match") == "pegamento blanco"


def test_hygiene_trace_records_only_applied_changes():
    assert hygiene_trace("  ADHESIVOS ") == ("trim", "casefold")
    assert hygiene_trace("Café") == ("casefold", "strip_accents")
    assert hygiene_trace("N/A") == ("placeholder",)
    assert hygiene_trace("Adhesivos") == ("casefold",)


text = st.text(
    st.characters(min_codepoint=32, max_codepoint=0x024F),
    max_size=60,
)


@given(text)
def test_display_profile_is_idempotent(value):
    once = normalize(value, "display")
    assert normalize(once, "display") == once


@given(text)
def test_match_profile_is_idempotent(value):
    once = normalize(value, "match")
    assert normalize(once, "match") == once
