const API_URL = import.meta.env.VITE_API_URL;

function getToken() {
  return localStorage.getItem('token');
}

async function handleResponse(res) {
  if (res.status === 204) return null;

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    let data = null;
    try {
      data = await res.json();
      detail = data.detail || JSON.stringify(data);
    } catch {
      // ignore parse errors, use default detail
    }
    const err = new Error(detail);
    err.status = res.status;
    err.data = data;
    throw err;
  }

  const text = await res.text();
  return text ? JSON.parse(text) : null;
}

async function request(path, { method = 'GET', body } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  const token = getToken();
  if (token) headers['Authorization'] = `Token ${token}`;

  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  return handleResponse(res);
}

// For file uploads: no Content-Type header (the browser sets the multipart
// boundary itself) and no JSON.stringify — `formData` is sent as-is.
async function requestForm(path, formData, { method = 'POST' } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers['Authorization'] = `Token ${token}`;

  const res = await fetch(`${API_URL}${path}`, { method, headers, body: formData });

  return handleResponse(res);
}

export const api = {
  login: (username, password) =>
    request('/auth/login/', { method: 'POST', body: { username, password } }),
  me: () => request('/auth/me/'),

  listClients: () => request('/clients/'),
  createClient: (data) => request('/clients/', { method: 'POST', body: data }),
  updateClient: (id, data) => request(`/clients/${id}/`, { method: 'PATCH', body: data }),
  deleteClient: (id) => request(`/clients/${id}/`, { method: 'DELETE' }),
  getClient: (id) => request(`/clients/${id}/`),

  listSystems: () => request('/systems/'),
  createSystem: (data) => request('/systems/', { method: 'POST', body: data }),
  updateSystem: (id, data) => request(`/systems/${id}/`, { method: 'PATCH', body: data }),
  deleteSystem: (id) => request(`/systems/${id}/`, { method: 'DELETE' }),

  currentTimeEntry: () => request('/time-entries/current/'),
  startTimeEntry: (data) => request('/time-entries/start/', { method: 'POST', body: data }),
  stopTimeEntry: (id) => request(`/time-entries/${id}/stop/`, { method: 'POST' }),
  cancelTimeEntry: (id) => request(`/time-entries/${id}/cancel/`, { method: 'POST' }),
  resumeTimeEntry: (id) => request(`/time-entries/${id}/resume/`, { method: 'POST' }),
  logManualHours: (data) => request('/time-entries/manual/', { method: 'POST', body: data }),

  listBilling: (year, month, clientId) =>
    request(`/billing/?year=${year}&month=${month}${clientId ? `&client=${clientId}` : ''}`),
  togglePaid: (id) => request(`/billing/${id}/toggle-paid/`, { method: 'POST' }),

  listTimeEntriesForClient: (clientId) => request(`/time-entries/?client=${clientId}`),

  listWorkers: () => request('/workers/'),
  createWorker: (data) => request('/workers/', { method: 'POST', body: data }),
  getWorker: (id) => request(`/workers/${id}/`),
  updateWorker: (id, data) => request(`/workers/${id}/`, { method: 'PATCH', body: data }),
  deleteWorker: (id) => request(`/workers/${id}/`, { method: 'DELETE' }),
  getWorkerSummary: (id, year, month) => request(`/workers/${id}/summary/?year=${year}&month=${month}`),

  getMySummary: (year, month) => request(`/me/summary/?year=${year}&month=${month}`),
  changePassword: (data) => request('/auth/change-password/', { method: 'POST', body: data }),

  listReceipts: (clientId, year, month) =>
    request(`/receipts/?client=${clientId}&year=${year}&month=${month}`),

  listReceiptChat: () => request('/receipt-chat/'),
  uploadReceiptChat: (imageFile) => {
    const fd = new FormData();
    fd.append('image', imageFile);
    return requestForm('/receipt-chat/', fd);
  },
  approveReceiptChat: (id, fields) =>
    request(`/receipt-chat/${id}/approve/`, { method: 'POST', body: fields }),
  discardReceiptChat: (id) => request(`/receipt-chat/${id}/discard/`, { method: 'POST' }),
  retryReceiptChat: (id) => request(`/receipt-chat/${id}/retry/`, { method: 'POST' }),
};
