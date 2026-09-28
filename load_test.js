import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '5s', target: 10 },  // Підйом навантаження до 10 користувачів
    { duration: '15s', target: 10 }, // Стабільні 10 користувачів
    { duration: '5s', target: 0 },   // Зниження до 0
  ],
  thresholds: {
    // SLO 1: 95% запитів мають виконуватися швидше 250 мс
    http_req_duration: ['p(95)<250'],
    // SLO 2: частка помилок менше 1%
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  // Викликаємо робочий ендпоінт розрахунку прогнозу часу
  const url = 'http://127.0.0.1:8000/api/plans/race/forecast?known_distance_km=5&known_time_sec=1500&race=10k';

  const res = http.get(url);

  check(res, {
    'status is 200': (r) => r.status === 200,
  });

  sleep(0.05);
}