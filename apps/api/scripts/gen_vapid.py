"""Genera un par de claves VAPID para las notificaciones push.

Uso: uv run python -m scripts.gen_vapid

Copia las dos líneas en el .env de la API (y en el del servidor). La clave privada no se
comparte con nadie; la pública la pide la web para suscribirse.
"""

import base64

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid


def main() -> None:
    vapid = Vapid()
    vapid.generate_keys()

    private_raw = vapid.private_key.private_numbers().private_value.to_bytes(32, "big")
    public_raw = vapid.public_key.public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )

    def b64url(raw: bytes) -> str:
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    print(f"PSST_VAPID_PRIVATE_KEY={b64url(private_raw)}")
    print(f"PSST_VAPID_PUBLIC_KEY={b64url(public_raw)}")


if __name__ == "__main__":
    main()
