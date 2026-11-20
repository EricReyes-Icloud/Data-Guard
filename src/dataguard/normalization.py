import re
import unicodedata
from typing import Literal

Profile = Literal["display", "match"]

PLACEHOLDERS = frozenset({"", "-", "n/a"})
WHITESPACE = re.compile(r"\s+")


def _fold_whitespace(text: str) -> str:
    return WHITESPACE.sub(" ", text).strip()


def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(
        char for char in decomposed if unicodedata.category(char) != "Mn"
    )


def _strip_punctuation(text: str) -> str:
    return "".join(
        char if (char.isalnum() or char.isspace()) else " " for char in text
    )


def normalize(value: str, profile: Profile = "match") -> str:
    """Normaliza un valor con uno de dos perfiles.

    ``display`` conserva mayúsculas y acentos: es la higiene mínima que se
    escribe en la hoja limpia. ``match`` es agresiva y solo se usa para
    comparar contra el catálogo; su resultado nunca se escribe en la salida.
    """
    text = _fold_whitespace(unicodedata.normalize("NFKC", value))
    if text.casefold() in PLACEHOLDERS:
        return ""
    if profile == "display":
        return text

    text = _strip_accents(text.casefold())
    text = _fold_whitespace(_strip_punctuation(text))
    return "" if text in PLACEHOLDERS else text


def hygiene_trace(value: str) -> tuple[str, ...]:
    """Registra, en orden estable, qué normalizaciones cambiaron el valor."""
    applied: list[str] = []
    display = normalize(value, "display")
    matched = normalize(value, "match")

    if value != value.strip():
        applied.append("trim")
    if WHITESPACE.search(value.strip()) and WHITESPACE.search(value.strip()).group() != " ":
        applied.append("whitespace_collapse")
    if display == "":
        applied.append("placeholder")
    if display and display.casefold() != display:
        applied.append("casefold")
    if display and _strip_accents(display.casefold()) != display.casefold():
        applied.append("strip_accents")
    if display and _strip_punctuation(display.casefold()) != display.casefold():
        applied.append("strip_punctuation")
    if not applied and matched != display:
        applied.append("normalization")

    return tuple(applied)
