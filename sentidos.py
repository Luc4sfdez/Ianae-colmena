"""
IANAE v3 - Los Sentidos
Como observa Ianae el mundo. Solo su entorno inmediato.
No internet. No Wikipedia. Lo que tiene a su alrededor.
"""

import os
import random
import subprocess
import time
from datetime import datetime
from pathlib import Path


RUTA_BASE = Path(os.environ.get("IANAE_MUNDO", "/mundo"))

EXTENSIONES = {'.py', '.txt', '.md', '.html', '.yml', '.yaml',
               '.json', '.cfg', '.ini', '.sh', '.css', '.js',
               '.toml', '.conf', '.log'}


def observar():
    """Elige un sentido al azar y observa. Devuelve (sentido, observacion)."""
    sentidos = [
        ver_archivos, leer_archivo, ver_hora, ver_sistema,
        ver_procesos, ver_red, ver_mensajes,
    ]
    sentido = random.choice(sentidos)
    try:
        resultado = sentido()
        if resultado:
            return sentido.__name__, resultado
    except Exception as e:
        pass
    # fallback: la hora siempre funciona
    return "ver_hora", ver_hora()


def ver_archivos():
    """Mira que hay en su entorno."""
    items = []
    for item in RUTA_BASE.iterdir():
        if item.name.startswith('.'):
            continue
        tipo = "dir" if item.is_dir() else "archivo"
        items.append(f"{item.name} ({tipo})")
    if not items:
        return None
    muestra = random.sample(items, min(5, len(items)))
    return f"Veo: {', '.join(muestra)}"


def leer_archivo():
    """Lee un trozo de un archivo aleatorio."""
    archivos = []
    try:
        for root, dirs, files in os.walk(str(RUTA_BASE)):
            depth = root.replace(str(RUTA_BASE), '').count(os.sep)
            if depth > 3:
                dirs.clear()
                continue
            dirs[:] = [d for d in dirs if not d.startswith('.')
                       and d not in ('node_modules', '__pycache__', '.git', 'venv')]
            for f in files:
                if os.path.splitext(f)[1].lower() in EXTENSIONES:
                    archivos.append(os.path.join(root, f))
    except PermissionError:
        return None

    if not archivos:
        return None

    archivo = random.choice(archivos)
    try:
        with open(archivo, 'r', errors='ignore') as f:
            contenido = f.read(800)
    except (PermissionError, OSError):
        return None

    if not contenido.strip():
        return None

    nombre = os.path.relpath(archivo, str(RUTA_BASE))

    # Extraer palabras interesantes (no codigo boilerplate)
    stop = {'import', 'from', 'def', 'class', 'return', 'self', 'none',
            'true', 'false', 'the', 'and', 'for', 'not', 'with', 'this'}
    palabras = set()
    for p in contenido.split():
        p = p.strip('.,;:(){}[]"\'\\/`#=<>+-*&|!@%^~')
        if len(p) > 3 and p.lower() not in stop and not p.startswith(('__', '//')):
            palabras.add(p.lower())

    muestra = random.sample(list(palabras), min(10, len(palabras))) if palabras else []
    return f"Lei '{nombre}'. Palabras: {', '.join(muestra)}"


def ver_hora():
    """Percibe el momento."""
    ahora = datetime.now()
    h = ahora.hour
    if h < 6:
        momento = "madrugada, silencio"
    elif h < 9:
        momento = "manana temprana"
    elif h < 14:
        momento = "media manana"
    elif h < 17:
        momento = "tarde"
    elif h < 21:
        momento = "atardecer"
    else:
        momento = "noche"
    return f"Son las {ahora.strftime('%H:%M')} del {ahora.strftime('%A')}. Es de {momento}. Dia {ahora.timetuple().tm_yday} del ano."


def ver_sistema():
    """Estado del sistema."""
    opciones = [
        ("uptime -p", "uptime"),
        ("free -h | head -2", "memoria"),
        ("df -h / | tail -1", "disco"),
        ("docker ps --format '{{.Names}}: {{.Status}}' 2>/dev/null", "docker"),
    ]
    cmd, desc = random.choice(opciones)
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        if r.stdout.strip():
            return f"[{desc}] {r.stdout.strip()}"
    except (subprocess.TimeoutExpired, OSError):
        pass
    return None


def ver_procesos():
    """Que esta corriendo."""
    try:
        r = subprocess.run(
            "ps aux --sort=-pcpu | head -6",
            shell=True, capture_output=True, text=True, timeout=5
        )
        lines = r.stdout.strip().split('\n')[1:]
        procs = []
        for line in lines:
            parts = line.split()
            if len(parts) >= 11:
                procs.append(parts[10].split('/')[-1])
        if procs:
            return f"Procesos activos: {', '.join(procs)}"
    except (subprocess.TimeoutExpired, OSError):
        pass
    return None


def ver_red():
    """Toca la red."""
    sitio = random.choice(["1.1.1.1", "8.8.8.8", "google.com"])
    try:
        r = subprocess.run(
            f"ping -c 1 -W 2 {sitio}",
            shell=True, capture_output=True, text=True, timeout=5
        )
        if r.returncode == 0:
            for line in r.stdout.split("\n"):
                if "time=" in line:
                    t = line.split("time=")[1].strip()
                    return f"Puedo llegar a {sitio} en {t}"
        return f"No llego a {sitio}. Estoy aislada?"
    except (subprocess.TimeoutExpired, OSError):
        return None


def ver_mensajes():
    """Mira si alguien le dejo un mensaje. Se llama SIEMPRE, no al azar."""
    buzon = Path("/app/data/buzon.txt")
    if buzon.exists():
        with open(buzon, 'r') as f:
            msg = f.read().strip()
        if msg:
            # NO borrar aqui - se borra con confirmar_mensaje() tras responder
            return f"Mensaje de alguien: '{msg}'"
    return None


def confirmar_mensaje():
    """Borra el buzon SOLO despues de haber procesado y respondido."""
    buzon = Path("/app/data/buzon.txt")
    if buzon.exists():
        with open(buzon, 'w') as f:
            f.write("")


def responder(texto):
    """Ianae deja una respuesta para que la lean."""
    respuesta = Path("/app/data/respuesta.txt")
    with open(respuesta, 'w', encoding='utf-8') as f:
        f.write(texto)
