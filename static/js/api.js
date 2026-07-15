const API_BASE = '/api/v1';

export async function apiRequest(endpoint, options = {}) {
  const token = localStorage.getItem('studymate-token');
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    localStorage.removeItem('studymate-token');
    localStorage.removeItem('studymate-user');
    window.location.href = '/login';
    throw new Error('Session expired');
  }

  return res;
}

export async function apiPost(endpoint, body) {
  return apiRequest(endpoint, { method: 'POST', body: JSON.stringify(body) });
}

export async function apiGet(endpoint) {
  return apiRequest(endpoint, { method: 'GET' });
}

export async function apiPatch(endpoint, body) {
  return apiRequest(endpoint, { method: 'PATCH', body: JSON.stringify(body) });
}

export async function apiDelete(endpoint) {
  return apiRequest(endpoint, { method: 'DELETE' });
}

export function getAuthHeaders() {
  const token = localStorage.getItem('studymate-token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}
