"""Escribe el esquema OpenAPI de la API en un fichero JSON, sin arrancar el servidor.

Uso: uv run python -m scripts.export_openapi <ruta de salida>

La web genera sus tipos TypeScript a partir de ese fichero (`pnpm gen:api`).
"""

import json
import sys
from pathlib import Path

from app.main import app


def main() -> None:
    output = Path(sys.argv[1])
    schema = json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(schema, encoding="utf-8", newline="\n")
    print(f"OpenAPI escrito en {output}")


if __name__ == "__main__":
    main()
