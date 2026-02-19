FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    iputils-ping iproute2 procps && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY mente.py sentidos.py diario.py ciclo.py reuniones.py \
     memoria.py rag.py resumenes.py ollama_client.py ./
RUN mkdir -p data diario

CMD ["python", "-u", "ciclo.py"]
