import argparse
import json
from pathlib import Path

from dataguard.engine import validate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dataguard", description="Valida el Excel del proveedor")
    sub = parser.add_subparsers(dest="command", required=True)

    validar = sub.add_parser("validar", help="Valida un archivo de proveedor")
    validar.add_argument("archivo_proveedor")
    validar.add_argument("--proveedor", required=True, help="Ruta al YAML de configuración del proveedor")
    validar.add_argument("--salida", default=None, help="Directorio de salida (por defecto: junto al archivo)")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "validar":
        result = validate(
            args.archivo_proveedor,
            args.proveedor,
            output_dir=args.salida,
        )
        print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
        return 0

    parser.print_help()
    return 1
