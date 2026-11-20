const call = async (path, options = {}) => {
  const response = await fetch(`/api${path}`, { credentials: 'include', ...options });
  if (response.status === 204) return null;
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.message || 'Request failed');
  return body;
};

export const login = (email, password, role) => call('/auth/login', {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email, password, role })
});
export const logout = () => call('/auth/logout', { method: 'POST' });
export const me = () => call('/auth/me');
export const listRequests = () => call('/requests?pageSize=100');
export const getStats = () => call('/stats');
export const createRequest = (data, file) => {
  const form = new FormData();
  Object.entries(data).forEach(([key, value]) => form.append(key, value));
  if (file) form.append('attachment', file);
  return call('/requests', { method: 'POST', body: form });
};
