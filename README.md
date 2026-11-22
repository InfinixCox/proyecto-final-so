# Proyecto final de Sistemas Operativos: infraestructura con Docker, Nginx, Prometheus y Grafana

**Autores:** Juan Steban Burbano y Juan David Alvarez Arce

Infraestructura en contenedores con un proxy inverso Nginx que reparte el tráfico entre 3 backends, y un sistema de monitoreo con Prometheus, Grafana, nginx-exporter y cAdvisor.

## Arquitectura

```
                          Red Docker "proyecto-so-net"
 +---------+   8080   +-------+      +-----------+
 | Cliente | -------> | Nginx | ---> | backend-1 |  (Flask + Gunicorn, /metrics)
 | (k6 /   |          | proxy | ---> | backend-2 |
 | navegador)         | inv.  | ---> | backend-3 |
 +---------+          +---+---+      +-----+-----+
                          | stub_status    | /metrics
                   +------v-------+        |
                   | nginx-exporter|       |
                   +------+-------+        |
        +----------+      |                |
        | cAdvisor |      |                |
        +----+-----+      |                |
             +------------+----------------+
                          v
                    +------------+        +---------+
                    | Prometheus | -----> | Grafana |
                    +------------+        +---------+
```

| Servicio | Función |
|---|---|
| `nginx` | Proxy inverso y balanceador (round robin) hacia los 3 backends |
| `backend1`, `backend2`, `backend3` | Tres contenedores de la misma aplicación Flask: se construyen desde una sola carpeta (`backend/`) y usan la misma imagen (`proyecto-so-backend:1.0`). Cada uno recibe su número en la variable de entorno `INSTANCE` (definida en `docker-compose.yml`), se identifica como backend-1, 2 o 3 y expone `/metrics` con prometheus-flask-exporter |
| `nginx-exporter` | Traduce el `stub_status` de Nginx al formato de Prometheus |
| `cadvisor` | Mide CPU, memoria, red y disco de cada contenedor |
| `prometheus` | Recoge las métricas cada 5 s y las guarda en un volumen |
| `grafana` | Dibuja los dashboards, que se cargan solos al iniciar |

## Requisitos previos

- Docker y Docker Compose (Docker Desktop en Windows y macOS, o Docker Engine en Linux)
- k6 para las pruebas de carga, instalado en la máquina física:
  - Windows: `winget install k6 --source winget`
  - macOS: `brew install k6`
  - Linux: <https://grafana.com/docs/k6/latest/set-up/install-k6/>
- Puertos libres: 8080, 8081, 9090 y 3000 (se pueden cambiar copiando `.env.example` a `.env`)
- Se recomienda dar al menos 4 GB de memoria a Docker Desktop

## Levantar la infraestructura

```bash
git clone <URL-DEL-REPOSITORIO>
cd <carpeta-del-repositorio>
docker compose up -d --build
docker compose ps
```

Los 8 contenedores deben aparecer en estado `running`, y los 3 backends en `healthy`.

> **Windows con Docker Desktop + WSL:** el proyecto se probó ejecutando los comandos desde Ubuntu (WSL 2) con la integración WSL de Docker Desktop activada. El servicio `cadvisor` ya trae los ajustes necesarios para ese entorno (ver "Solución de problemas").

## Direcciones de acceso

| Servicio | URL | Nota |
|---|---|---|
| Aplicación (a través de Nginx) | <http://localhost:8080> | Recarga con F5 y cambia de backend |
| Prometheus | <http://localhost:9090> | Status, Target health |
| Grafana | <http://localhost:3000> | Se ve sin iniciar sesión. Para editar: `admin` / `admin` |
| cAdvisor | <http://localhost:8081> | Docker Containers |

## Verificar el balanceo de carga

1. Abre <http://localhost:8080> y recarga varias veces: la página cambia entre Backend 1, 2 y 3.
2. Por terminal, 9 peticiones seguidas:

   ```bash
   # bash (Linux, macOS, WSL)
   for i in $(seq 9); do curl -s http://localhost:8080/api/info; echo; done
   ```
   ```powershell
   # PowerShell
   1..9 | ForEach-Object { (curl.exe -s http://localhost:8080/api/info | ConvertFrom-Json).backend }
   ```

   Debe salir backend-1, backend-2, backend-3, y repetirse.
3. Ver qué backend atendió cada petición en el log de Nginx:

   ```bash
   docker compose logs nginx
   ```
4. Con k6 (30 peticiones, cuenta cuántas atendió cada backend):

   ```bash
   k6 run load-tests/smoke.js
   ```

## Verificar el monitoreo

1. En Prometheus, **Status > Target health**: deben aparecer **6 targets en UP** (prometheus, 3 backends, nginx-exporter y cadvisor).
2. En Prometheus, **Query**, prueba por ejemplo:
   - `sum by (backend) (rate(flask_http_request_total[30s]))`
   - `histogram_quantile(0.95, sum by (le, backend) (rate(flask_http_request_duration_seconds_bucket[30s])))`
   - `sum by (name) (rate(container_cpu_usage_seconds_total{name!=""}[30s]))`
3. En Grafana (<http://localhost:3000>) se abre directamente el dashboard **Infraestructura Proyecto Final**, con peticiones por segundo, latencia p95, errores, CPU, memoria, red, disco y estado de Nginx.

## Pruebas de carga (k6, desde la máquina física)

```bash
mkdir results
k6 run --summary-export=results/load.json load-tests/load.js     # carga normal, 4 minutos
k6 run --summary-export=results/stress.json load-tests/stress.js # saturación, 2,5 minutos
```

| Script | Qué hace |
|---|---|
| `smoke.js` | 30 peticiones para comprobar el reparto entre backends |
| `load.js` | Sube a 50 usuarios virtuales y se mantiene. Mezcla peticiones ligeras, con espera y con uso de CPU |
| `stress.js` | Sube hasta 80 peticiones por segundo con peticiones de 0,5 s, por encima de lo que aguantan los 3 backends |

Mientras corren, observa el dashboard de Grafana.

### Prueba de falla de un backend

1. Lanza `k6 run load-tests/load.js`.
2. En otra terminal: `docker compose stop backend2`
3. En Grafana, backend-2 baja a 0 y los otros dos absorben la carga. En Prometheus, `up{job="backends"}` pasa a 0 para ese backend.
4. Recupéralo: `docker compose start backend2`. Nginx lo vuelve a usar en unos 10 segundos.

### Prueba de persistencia

```bash
docker compose down      # apaga y elimina contenedores, conserva los volúmenes
docker compose up -d
```

Prometheus y Grafana conservan sus datos. Para borrar también los datos: `docker compose down -v`.

## Estructura del proyecto

```
.
├── docker-compose.yml          # los 8 servicios, la red y los volúmenes
├── backend/                    # una sola imagen para los 3 backends
│   ├── Dockerfile
│   ├── app.py                  # aplicación Flask con prometheus-flask-exporter
│   └── requirements.txt
├── nginx/nginx.conf            # proxy inverso, balanceo y stub_status
├── monitoring/
│   ├── prometheus/             # prometheus.yml y alerts.yml
│   └── grafana/                # fuente de datos y dashboard cargados automáticamente
├── load-tests/                 # scripts de k6
└── .env.example                # puertos configurables
```

## Solución de problemas

- **cAdvisor no ve los contenedores o los paneles de CPU, memoria y red salen vacíos (Docker Desktop + WSL):** las rutas que se montan desde WSL (`/`, `/var/run`) son las de la distribución Ubuntu, no las de la máquina virtual de Docker Desktop, así que cAdvisor no encontraba el socket de containerd (`/run/containerd/containerd.sock`) y en los logs aparecía `Registration of the docker container factory failed`. El `docker-compose.yml` ya incluye la solución:
  - `pid: host`: cAdvisor ve los procesos de la máquina virtual de Docker Desktop.
  - `--containerd=/proc/1/root/run/containerd/containerd.sock`: llega al socket de containerd a través del sistema de archivos del proceso 1 de esa máquina virtual.
  - `cgroup: host`: ve los cgroups del anfitrión (cgroup v2).
  - Se desactivó el montaje `/:/rootfs`, que desde WSL apuntaba a Ubuntu y hacía que la red por contenedor saliera incompleta.
  Para comprobarlo: `docker logs cadvisor 2>&1 | grep factory` debe mostrar `Registration of the docker container factory successfully`.
- **Puerto ocupado o "forbidden by its access permissions":** Windows reserva rangos de puertos. Copia `.env.example` a `.env` y cambia el puerto.
- **Nginx no ve un backend recreado:** `docker compose restart nginx`.
- **Los paneles salen vacíos:** espera 30 segundos y genera carga, porque `rate()` necesita varias lecturas.
