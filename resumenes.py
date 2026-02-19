"""
IANAE v3 - Resumenes Periodicos
Cada X ciclos, Ianae resume lo aprendido con Ollama y lo guarda.
Conocimiento condensado que persiste mas que el diario crudo.
"""

import os
from datetime import datetime
from pathlib import Path

import diario
import ollama_client

RESUMENES_DIR = Path(__file__).parent / "data" / "resumenes"


def _guardar(texto, fuente="ollama"):
    """Guarda un resumen en fichero. Siempre."""
    RESUMENES_DIR.mkdir(parents=True, exist_ok=True)
    fecha = datetime.now().strftime("%Y-%m-%d")
    archivo = RESUMENES_DIR / f"{fecha}.txt"
    modo = "a" if archivo.exists() else "w"
    hora = datetime.now().strftime("%H:%M")
    with open(archivo, modo, encoding="utf-8") as f:
        f.write(f"[{hora}] ({fuente}) {texto}\n\n")


def hacer_resumen():
    """Lee el diario de hoy y genera un resumen con Ollama."""
    texto_diario = diario.leer_hoy()
    if not texto_diario or texto_diario == "(vacio)":
        return None

    # Truncar agresivamente: 4 instancias compiten por Ollama
    if len(texto_diario) > 800:
        texto_diario = texto_diario[:400] + "\n...\n" + texto_diario[-300:]

    resumen = ollama_client.resumir(texto_diario)
    if not resumen:
        return None

    _guardar(resumen, "ollama")
    return resumen


def guardar_basico(texto):
    """Guarda un resumen basico (sin Ollama). Para el fallback."""
    _guardar(texto, "basico")


def ultimo_resumen():
    """Devuelve el resumen mas reciente."""
    RESUMENES_DIR.mkdir(parents=True, exist_ok=True)
    archivos = sorted(RESUMENES_DIR.glob("*.txt"), reverse=True)
    if archivos:
        try:
            return archivos[0].read_text(encoding="utf-8").strip()
        except OSError:
            pass
    return None


def total_resumenes():
    """Cuantos dias tiene resumidos."""
    RESUMENES_DIR.mkdir(parents=True, exist_ok=True)
    return len(list(RESUMENES_DIR.glob("*.txt")))
