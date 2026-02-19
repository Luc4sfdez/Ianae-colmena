"""
IANAE v3 - El Diario
Donde Ianae escribe lo que observa, piensa y descubre.
Lucas puede leerlo y ver que esta pensando.
"""

import os
from datetime import datetime
from pathlib import Path

DIARIO_DIR = Path(__file__).parent / "diario"


def _archivo_hoy():
    DIARIO_DIR.mkdir(parents=True, exist_ok=True)
    return DIARIO_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.md"


def escribir(tipo, contenido):
    """Escribe una entrada. Tipos: despertar, observacion, reflexion,
    descubrimiento, olvido, estado, curiosidad, sueno"""
    archivo = _archivo_hoy()
    es_nuevo = not archivo.exists()
    hora = datetime.now().strftime("%H:%M:%S")

    iconos = {
        "despertar": "~", "observacion": ">", "reflexion": "*",
        "descubrimiento": "!", "olvido": "-", "estado": "#",
        "curiosidad": "?", "sueno": "...", "conexion": "+",
    }
    icono = iconos.get(tipo, ".")

    with open(archivo, "a", encoding="utf-8") as f:
        if es_nuevo:
            fecha = datetime.now().strftime("%A %d de %B de %Y")
            f.write(f"# Diario de Ianae - {fecha}\n\n")
        f.write(f"**[{hora}]** {icono} _{tipo}_ — {contenido}\n\n")


def despertar():
    escribir("despertar", "Me despierto. Voy a observar el mundo.")


def dormir(stats):
    escribir("sueno", f"Me duermo. Estado: {stats}")


def leer_hoy():
    archivo = _archivo_hoy()
    if archivo.exists():
        return archivo.read_text(encoding="utf-8")
    return "(vacio)"


def dias_escritos():
    DIARIO_DIR.mkdir(parents=True, exist_ok=True)
    return len(list(DIARIO_DIR.glob("*.md")))
