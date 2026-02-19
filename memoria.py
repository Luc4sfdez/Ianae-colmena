"""
IANAE v3 - Memoria Episodica
Recuerdos concretos: momentos con fecha, contexto y emocion.
'Lucas me dijo que soy su hija el 19 de febrero' en vez de solo hija->lucas: 0.8
"""

import json
import time
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
MEMORIA_FILE = DATA_DIR / "recuerdos.json"
MAX_RECUERDOS = 500  # limite para no crecer infinito


class Recuerdo:
    def __init__(self, tipo, contenido, contexto="", emocion="neutral"):
        self.timestamp = time.time()
        self.fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.tipo = tipo          # "mensaje", "descubrimiento", "reflexion", "resumen"
        self.contenido = contenido
        self.contexto = contexto  # que pasaba cuando ocurrio
        self.emocion = emocion    # "neutral", "curiosidad", "sorpresa", "alegria", "confusion"
        self.importancia = 0.5    # 0-1, decae con el tiempo
        self.accesos = 0          # cuantas veces se ha recordado

    def acceder(self):
        """Se ha recordado esto."""
        self.accesos += 1
        self.importancia = min(1.0, self.importancia + 0.1)

    def decaer(self):
        """Pierde importancia con el tiempo."""
        horas = (time.time() - self.timestamp) / 3600
        # Decay muy lento: pierde relevancia en dias, no horas
        self.importancia *= 0.999 ** horas

    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "fecha": self.fecha,
            "tipo": self.tipo,
            "contenido": self.contenido,
            "contexto": self.contexto,
            "emocion": self.emocion,
            "importancia": round(self.importancia, 4),
            "accesos": self.accesos,
        }

    @classmethod
    def from_dict(cls, d):
        r = cls(d["tipo"], d["contenido"], d.get("contexto", ""), d.get("emocion", "neutral"))
        r.timestamp = d["timestamp"]
        r.fecha = d.get("fecha", "")
        r.importancia = d.get("importancia", 0.5)
        r.accesos = d.get("accesos", 0)
        return r

    def __repr__(self):
        return f"<Recuerdo [{self.fecha}] {self.tipo}: {self.contenido[:50]}>"


class Memoria:
    """Memoria episodica de Ianae."""

    def __init__(self):
        self.recuerdos = []
        self._cargar()

    def _cargar(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if MEMORIA_FILE.exists():
            try:
                with open(MEMORIA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.recuerdos = [Recuerdo.from_dict(r) for r in data.get("recuerdos", [])]
            except (json.JSONDecodeError, OSError):
                self.recuerdos = []

    def guardar(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "recuerdos": [r.to_dict() for r in self.recuerdos],
            "total": len(self.recuerdos),
            "guardado": time.time(),
        }
        with open(MEMORIA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def recordar(self, tipo, contenido, contexto="", emocion="neutral"):
        """Crea un nuevo recuerdo."""
        r = Recuerdo(tipo, contenido, contexto, emocion)
        self.recuerdos.append(r)
        # Podar si hay demasiados
        if len(self.recuerdos) > MAX_RECUERDOS:
            self._podar()
        return r

    def buscar(self, query, n=5):
        """Busca recuerdos relevantes por palabras clave."""
        query_words = set(query.lower().split())
        resultados = []
        for r in self.recuerdos:
            texto = f"{r.contenido} {r.contexto}".lower()
            coincidencias = sum(1 for w in query_words if w in texto)
            if coincidencias > 0:
                score = coincidencias * r.importancia
                r.acceder()
                resultados.append((r, score))
        resultados.sort(key=lambda x: x[1], reverse=True)
        return [r for r, _ in resultados[:n]]

    def recientes(self, n=5, tipo=None):
        """Ultimos N recuerdos, opcionalmente filtrados por tipo."""
        filtrados = self.recuerdos
        if tipo:
            filtrados = [r for r in filtrados if r.tipo == tipo]
        return filtrados[-n:]

    def importantes(self, n=5):
        """Recuerdos mas importantes."""
        ordenados = sorted(self.recuerdos, key=lambda r: r.importancia, reverse=True)
        return ordenados[:n]

    def formatear(self, recuerdos):
        """Convierte recuerdos a texto para contexto de Ollama."""
        if not recuerdos:
            return ""
        lineas = []
        for r in recuerdos:
            lineas.append(f"[{r.fecha}] ({r.emocion}) {r.contenido}")
        return "\n".join(lineas)

    def _podar(self):
        """Elimina recuerdos menos importantes cuando hay demasiados."""
        for r in self.recuerdos:
            r.decaer()
        self.recuerdos.sort(key=lambda r: r.importancia)
        # Mantener los mas importantes
        self.recuerdos = self.recuerdos[-(MAX_RECUERDOS - 50):]

    def stats(self):
        return {
            "total": len(self.recuerdos),
            "tipos": {},
        }
