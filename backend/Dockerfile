# Imagen base ligera de Python
FROM python:3.12-slim

# Los logs salen al instante en "docker compose logs"
ENV PYTHONUNBUFFERED=1

# La identidad de cada backend (INSTANCE) NO va aqui: la misma imagen sirve
# para los 3 contenedores y docker-compose.yml le da a cada uno su INSTANCE
WORKDIR /app

# Primero las dependencias, para que Docker reutilice esta capa
# si solo cambia app.py
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# El proceso no corre como root
RUN useradd --no-create-home --shell /usr/sbin/nologin appuser
USER appuser

EXPOSE 5000

# Un solo proceso con 8 hilos: los contadores de Prometheus viven en
# memoria, con varios procesos cada uno tendria cifras distintas
CMD ["gunicorn", "-w", "1", "--threads", "8", "-b", "0.0.0.0:5000", "app:app"]
