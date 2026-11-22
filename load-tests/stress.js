// Prueba de saturacion: sube las peticiones por segundo hasta pasar la
// capacidad. Cada peticion tarda 0,5 s y cada backend atiende 8 a la vez,
// asi que 3 backends aguantan unas 48 peticiones por segundo.
// Uso:  k6 run load-tests/stress.js
import http from 'k6/http';
import { check } from 'k6';

const BASE = __ENV.BASE_URL || 'http://localhost:8080';

export const options = {
  scenarios: {
    saturacion: {
      executor: 'ramping-arrival-rate',
      startRate: 10,
      timeUnit: '1s',
      preAllocatedVUs: 100,
      maxVUs: 500,
      stages: [
        { duration: '30s', target: 30 },   // por debajo de la capacidad
        { duration: '30s', target: 60 },   // pasa la capacidad
        { duration: '1m', target: 80 },    // saturado
        { duration: '30s', target: 10 },   // recuperacion
      ],
    },
  },
  // Sin umbrales que cancelen: aqui queremos VER como se degrada
};

export default function () {
  const r = http.get(`${BASE}/api/work?ms=500`, { timeout: '10s' });
  check(r, { 'responde 200': (res) => res.status === 200 });
}
