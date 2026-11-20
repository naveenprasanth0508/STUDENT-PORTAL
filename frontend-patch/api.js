// REAL API client: replaces src/services/api.js. Same exports, so no page changes are needed.
const call = async (url, opts = {}) => {
  const res = await fetch(`/api${url}`, { credentials: 'include', ...opts });
  if (res.status === 204) return null;
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.message || 'Request failed');
  return body;
};
const json = (method, data) => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });

export const setSession = () => {}; // session lives in the httpOnly cookie
export const login = (c) => call('/auth/login', json('POST', c));
export const logout = () => call('/auth/logout', { method: 'POST' });
export const listRequests = (p = {}) => {
  const q = new URLSearchParams();
  Object.entries(p).forEach(([k, v]) => v !== '' && v != null && q.set(k, v));
  return call(`/requests?${q}`);
};
export const getRequest = (id) => call(`/requests/${id}`);
export const createRequest = ({ file, ...f }) => {
  const fd = new FormData();
  Object.entries(f).forEach(([k, v]) => fd.append(k, v));
  if (file) fd.append('attachment', file);
  return call('/requests', { method: 'POST', body: fd });
};
export const updateRequest = (id, p) => call(`/requests/${id}`, json('PATCH', p));
export const addReply = (id, message) => call(`/requests/${id}/replies`, json('POST', { message }));
export const addNote = (id, text) => call(`/requests/${id}/notes`, json('POST', { text }));
export const deleteRequest = (id) => call(`/requests/${id}`, { method: 'DELETE' });
export const listAdmins = () => call('/admins');
export const getStats = () => call('/stats');
