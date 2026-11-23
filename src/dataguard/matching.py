from dataclasses import dataclass

from rapidfuzz.distance import Indel
from rapidfuzz.fuzz import WRatio

from dataguard.catalog import Catalog
from dataguard.normalization import normalize


@dataclass(frozen=True)
class MatchResult:
    kind: str  # exact | alias | fuzzy | ambiguous | no_match
    canonical: str | None
    score: float | None
    candidates: tuple[tuple[str, float], ...]


def _best_by_category(value: str, catalog: Catalog) -> list[tuple[str, float]]:
    best: dict[str, float] = {}
    for key, canonical in catalog.aliases.items():
        score = float(WRatio(value, key))
        if score > best.get(canonical, -1.0):
            best[canonical] = score
    ranked = sorted(best.items(), key=lambda item: (-item[1], item[0]))
    return ranked


def match_category(value: str, catalog: Catalog) -> MatchResult:
    norm = normalize(value, "match")
    if norm == "":
        return MatchResult(kind="no_match", canonical=None, score=None, candidates=())

    if norm in catalog.categories:
        return MatchResult(kind="exact", canonical=norm, score=100.0, candidates=((norm, 100.0),))

    if norm in catalog.aliases:
        canonical = catalog.aliases[norm]
        # Si el alias es la propia categoría oficial ya se trató arriba.
        return MatchResult(kind="alias", canonical=canonical, score=100.0, candidates=((canonical, 100.0),))

    ranked = _best_by_category(norm, catalog)
    if not ranked:
        return MatchResult(kind="no_match", canonical=None, score=None, candidates=())

    top_category, top_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else -1.0
    margin = top_score - second_score

    if top_score >= 90 and margin >= 10:
        return MatchResult(
            kind="fuzzy",
            canonical=top_category,
            score=top_score,
            candidates=tuple(ranked[:3]),
        )

    if top_score >= 90 and margin < 10:
        return MatchResult(
            kind="ambiguous",
            canonical=None,
            score=top_score,
            candidates=tuple(ranked[:2]),
        )

    return MatchResult(kind="no_match", canonical=None, score=top_score, candidates=tuple(ranked[:2]))
