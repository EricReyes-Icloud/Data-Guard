from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class Estado(str, Enum):
    APROBADO = "aprobado"
    SUGERIDO = "sugerido"
    RECHAZADO = "rechazado"


class Severidad(str, Enum):
    CRITICAL = "critical"
    CORRECTIBLE = "correctible"
    WARNING = "warning"


@dataclass(frozen=True)
class Fila:
    numero: int
    producto: str
    categoria: str
    precio: Decimal | None
    higiene: tuple[str, ...]


@dataclass(frozen=True)
class Hallazgo:
    fila: int
    campo: str
    regla_id: str
    severidad: Severidad
    valor_original: str
    valor_sugerido: str | None = None
    score: float | None = None


@dataclass(frozen=True)
class Veredicto:
    fila: int
    estado: Estado
    hallazgos: tuple[Hallazgo, ...]


@dataclass(frozen=True)
class Rule:
    id: str
    field: str
    severity: Severidad
    check: Callable[[object], bool]
    message: str
