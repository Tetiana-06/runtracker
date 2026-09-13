/** Тонкий клієнт REST API RunTracker. */

const BASE_URL = '/api';

async function request(path, options = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${response.status}: ${detail}`);
  }

  return response.json();
}

export const api = {
  listRunners: () => request('/runners'),
  createRunner: (payload) => request('/runners', { method: 'POST', body: JSON.stringify(payload) }),
  zones: (runnerId) => request(`/runners/${runnerId}/zones`),

  listRuns: (runnerId) => request(`/runs?runner_id=${runnerId}`),
  createRun: (payload) => request('/runs', { method: 'POST', body: JSON.stringify(payload) }),
  weekly: (runnerId) => request(`/runs/summary/weekly?runner_id=${runnerId}`),
  insights: (runnerId) => request(`/runs/summary/insights?runner_id=${runnerId}`),

  listShoes: (runnerId) => request(`/shoes?runner_id=${runnerId}`),
  createShoe: (payload) => request('/shoes', { method: 'POST', body: JSON.stringify(payload) }),
  gearOverview: (runnerId) => request(`/shoes/overview/${runnerId}`),

  createPlan: (payload) => request('/plans', { method: 'POST', body: JSON.stringify(payload) }),
  latestPlan: (runnerId) => request(`/plans/${runnerId}/latest`),
};
