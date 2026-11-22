"""Backend de ejemplo para el proyecto final de Sistemas Operativos.

Los 3 contenedores usan esta misma imagen y cada uno se identifica con la
variable de entorno INSTANCE (1, 2 o 3), definida en docker-compose.yml.
Las metricas de /metrics las genera prometheus-flask-exporter, como en el
laboratorio de monitoreo.
"""
import math
import os
import random
import socket
import time

from flask import Flask, Response, jsonify, request
from prometheus_flask_exporter import PrometheusMetrics

INSTANCE = os.getenv("INSTANCE", "1")
BACKEND = f"backend-{INSTANCE}"
HOSTNAME = socket.gethostname()
INICIO = time.time()
COLORES = {"1": "#2563eb", "2": "#16a34a", "3": "#ea580c"}

app = Flask(__name__)

# ---------------------------------------------------------------- metricas
# Registra /metrics y cuenta cada peticion (total y duracion) por ruta.
# Todas las metricas llevan la etiqueta backend="backend-N".
# El healthcheck de Docker (/health) no se cuenta.
metrics = PrometheusMetrics(
    app,
    group_by="endpoint",
    default_labels={"backend": BACKEND},
    excluded_paths=["/health"],
)
metrics.info("app_info", "Informacion del backend", server=BACKEND)


@app.after_request
def cabecera_backend(resp):
    # Cabecera para saber que backend respondio (la leen los scripts de k6)
    resp.headers["X-Backend"] = BACKEND
    return resp


# ------------------------------------------------------------------- rutas
@app.route("/")
def inicio():
    color = COLORES.get(INSTANCE, "#444")
    html = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><title>{BACKEND}</title></head>
<body style="font-family:sans-serif;text-align:center;margin-top:12vh;
background:{color};color:white">
<h1 style="font-size:4rem;margin:0">Backend {INSTANCE}</h1>
<p>contenedor: {HOSTNAME}</p>
<p>Recarga la pagina (F5): Nginx te manda al siguiente backend</p>
</body></html>"""
    return Response(html, mimetype="text/html")


@app.route("/api/info")
def info():
    return jsonify(
        backend=BACKEND,
        instancia=int(INSTANCE),
        contenedor=HOSTNAME,
        uptime_segundos=round(time.time() - INICIO, 1),
    )


@app.route("/api/work")
def trabajo():
    """Simula una operacion lenta (esperando disco o red). No gasta CPU."""
    ms = min(max(request.args.get("ms", 100, type=int), 0), 5000)
    time.sleep(ms / 1000)
    return jsonify(backend=BACKEND, tipo="espera", ms=ms)


@app.route("/api/cpu")
def cpu():
    """Simula una operacion pesada: ocupa el procesador durante ms."""
    ms = min(max(request.args.get("ms", 50, type=int), 0), 2000)
    fin = time.perf_counter() + ms / 1000
    while time.perf_counter() < fin:
        math.sqrt(random.random())
    return jsonify(backend=BACKEND, tipo="cpu", ms=ms)


@app.route("/api/error")
def error():
    """Devuelve el codigo pedido (500 por defecto) para ver los errores en Grafana."""
    code = request.args.get("code", 500, type=int)
    if not 400 <= code <= 599:
        code = 500
    return jsonify(backend=BACKEND, error=code), code


@app.route("/health")
def health():
    return jsonify(status="ok", backend=BACKEND)
