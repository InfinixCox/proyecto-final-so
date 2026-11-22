// Prueba rapida de balanceo: 30 peticiones y cuenta cuantas atendio cada backend.
// Uso:  k6 run load-tests/smoke.js
import http from 'k6/http';
import { check } from 'k6';
import { Counter } from 'k6/metrics';

const BASE = __ENV.BASE_URL || 'http://localhost:8080';
const atendidas = new Counter('atendidas');

export const options = {
  vus: 1,
  iterations: 30,
  thresholds: {
    http_req_failed: ['rate<0.01'],
    // Estas lineas hacen que el resumen muestre cuantas atendio cada backend
    'atendidas{backend:backend-1}': ['count>0'],
    'atendidas{backend:backend-2}': ['count>0'],
    'atendidas{backend:backend-3}': ['count>0'],
  },
};

export default function () {
  const r = http.get(`${BASE}/api/info`);
  check(r, { 'responde 200': (res) => res.status === 200 });
  atendidas.add(1, { backend: r.headers['X-Backend'] });
}
