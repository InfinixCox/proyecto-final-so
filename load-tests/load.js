// Prueba de carga normal: sube de 0 a 50 usuarios virtuales y se mantiene.
// Mezcla peticiones ligeras, con espera y con uso de CPU.
// Uso:  k6 run load-tests/load.js
import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE = __ENV.BASE_URL || 'http://localhost:8080';

export const options = {
  stages: [
    { duration: '30s', target: 20 },  // calentamiento
    { duration: '1m', target: 50 },   // subida
    { duration: '2m', target: 50 },   // carga sostenida
    { duration: '30s', target: 0 },   // bajada
  ],
  thresholds: {
    http_req_failed: ['rate<0.01'],      // menos de 1 % de errores
    http_req_duration: ['p(95)<500'],    // p95 por debajo de 500 ms
  },
};

export default function () {
  const x = Math.random();
  let r;
  if (x < 0.7) {
    r = http.get(`${BASE}/api/info`);
  } else if (x < 0.9) {
    r = http.get(`${BASE}/api/work?ms=100`);
  } else {
    r = http.get(`${BASE}/api/cpu?ms=30`);
  }
  check(r, { 'responde 200': (res) => res.status === 200 });
  sleep(0.1 + Math.random() * 0.2);
}
