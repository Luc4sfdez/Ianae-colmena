"""
IANAE v3 - RAG (Retrieval Augmented Generation)
Busca en el historial de diarios para dar contexto a las respuestas.
Indice simple por palabras clave, sin embeddings (por ahora).
"""

import os
import re
from pathlib import Path
from collections import Counter


DIARIO_DIR = Path(__file__).parent / "diario"
RESUMENES_DIR = Path(__file__).parent / "data" / "resumenes"


def _tokenizar(texto):
    """Extrae palabras significativas de un texto."""
    texto = texto.lower()
    texto = re.sub(r'[^a-záéíóúñü\s]', ' ', texto)
    stop = {
        'para', 'como', 'este', 'esta', 'tiene', 'pero', 'todo', 'cada',
        'cuando', 'donde', 'algo', 'sido', 'estar', 'esta', 'esto',
        'unos', 'unas', 'otras', 'otros', 'mismo', 'misma', 'puede',
        'porque', 'desde', 'hasta', 'entre', 'sobre', 'durante',
        'antes', 'despues', 'siempre', 'nunca', 'veces', 'mucho',
        'poco', 'solo', 'tambien', 'aqui', 'ahora', 'hoy', 'ayer',
        'ciclo', 'estado', 'conozco', 'cosas', 'conexiones',
    }
    return [p for p in texto.split() if len(p) > 3 and p not in stop]


def buscar_en_diarios(query, max_resultados=5):
    """Busca entradas relevantes en todos los diarios."""
    DIARIO_DIR.mkdir(parents=True, exist_ok=True)
    query_tokens = set(_tokenizar(query))
    if not query_tokens:
        return []

    resultados = []
    for archivo in sorted(DIARIO_DIR.glob("*.md"), reverse=True)[:30]:  # ultimos 30 dias
        try:
            contenido = archivo.read_text(encoding="utf-8")
        except OSError:
            continue

        # Dividir en entradas (separadas por doble newline con timestamp)
        entradas = re.split(r'\n\n(?=\*\*\[)', contenido)
        for entrada in entradas:
            tokens = set(_tokenizar(entrada))
            coincidencias = query_tokens & tokens
            if coincidencias:
                score = len(coincidencias) / len(query_tokens)
                # Bonus por entradas mas recientes
                fecha = archivo.stem  # YYYY-MM-DD
                resultados.append({
                    "fecha": fecha,
                    "texto": entrada.strip()[:300],
                    "score": score,
                    "coincidencias": list(coincidencias),
                })

    resultados.sort(key=lambda x: x["score"], reverse=True)
    return resultados[:max_resultados]


def buscar_en_resumenes(query, max_resultados=3):
    """Busca en los resumenes condensados."""
    RESUMENES_DIR.mkdir(parents=True, exist_ok=True)
    query_tokens = set(_tokenizar(query))
    if not query_tokens:
        return []

    resultados = []
    for archivo in sorted(RESUMENES_DIR.glob("*.txt"), reverse=True)[:30]:
        try:
            contenido = archivo.read_text(encoding="utf-8")
        except OSError:
            continue

        tokens = set(_tokenizar(contenido))
        coincidencias = query_tokens & tokens
        if coincidencias:
            score = len(coincidencias) / len(query_tokens)
            resultados.append({
                "fecha": archivo.stem,
                "texto": contenido[:300],
                "score": score,
            })

    resultados.sort(key=lambda x: x["score"], reverse=True)
    return resultados[:max_resultados]


def contexto_para_respuesta(query, max_chars=800):
    """Busca en diarios + resumenes y devuelve contexto formateado."""
    resultados_diario = buscar_en_diarios(query, 3)
    resultados_resumen = buscar_en_resumenes(query, 2)

    partes = []
    chars = 0

    for r in resultados_resumen:
        trozo = f"[Resumen {r['fecha']}] {r['texto']}"
        if chars + len(trozo) > max_chars:
            break
        partes.append(trozo)
        chars += len(trozo)

    for r in resultados_diario:
        trozo = f"[Diario {r['fecha']}] {r['texto']}"
        if chars + len(trozo) > max_chars:
            break
        partes.append(trozo)
        chars += len(trozo)

    return "\n".join(partes)
