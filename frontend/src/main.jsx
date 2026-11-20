import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { createRequest, getStats, listRequests, login, logout, me } from './api';
import './styles.css';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [stats, setStats] = useState(null);
  const [requests, setRequests] = useState([]);

  const load = async () => {
    setError('');
    try {
      const [meResult, statsResult, listResult] = await Promise.all([me(), getStats(), listRequests()]);
      setUser(meResult.user); setStats(statsResult); setRequests(listResult.items);
    } catch (e) { setError(e.message); }
  };

  useEffect(() => { me().then(r => { setUser(r.user); load(); }).catch(() => {}).finally(() => setLoading(false)); }, []);

  const onLogin = async (event) => {
    event.preventDefault(); setError('');
    const form = new FormData(event.currentTarget);
    try { const r = await login(form.get('email'), form.get('password'), form.get('role')); setUser(r.user); await load(); }
    catch (e) { setError(e.message); }
  };

  const onCreate = async (event) => {
    event.preventDefault(); setError('');
    const form = new FormData(event.currentTarget);
    try {
      await createRequest({ subject: form.get('subject'), category: form.get('category'), priority: form.get('priority'), description: form.get('description') }, form.get('file'));
      event.currentTarget.reset(); await load();
    } catch (e) { setError(e.message); }
  };

  if (loading) return <main className="center">Loading portal…</main>;
  if (!user) return <main className="login-page"><form className="card login" onSubmit={onLogin}><h1>Student Portal</h1><p>Sign in to continue</p>{error && <div className="alert">{error}</div>}<label>Email<input name="email" type="email" required defaultValue="student@example.com"/></label><label>Password<input name="password" type="password" required/></label><label>Role<select name="role"><option value="student">Student</option><option value="admin">Admin</option></select></label><button type="submit">Sign in</button></form></main>;

  return <main className="app"><header><div><strong>Student Portal</strong><span>{user.name} · {user.role}</span></div><button className="secondary" onClick={async () => { await logout(); setUser(null); }}>Sign out</button></header><section className="content"><aside><h2>Overview</h2><div className="stats"><article><b>{stats?.total ?? 0}</b><span>Total requests</span></article>{Object.entries(stats?.counts ?? {}).map(([status, count]) => <article key={status}><b>{count}</b><span>{status}</span></article>)}</div>{user.role === 'student' && <form className="card create" onSubmit={onCreate}><h2>New request</h2>{error && <div className="alert">{error}</div>}<label>Subject<input name="subject" minLength="5" maxLength="100" required/></label><label>Category<select name="category"><option>Academic</option><option>Fee</option><option>Certificate</option><option>Hostel</option><option>Other</option></select></label><label>Priority<select name="priority"><option>Low</option><option>Medium</option><option>High</option></select></label><label>Description<textarea name="description" minLength="20" maxLength="5000" required/></label><label>Attachment<input name="file" type="file" accept=".pdf,image/png,image/jpeg"/></label><button type="submit">Submit request</button></form>}</aside><section className="requests"><h2>Requests</h2>{error && <div className="alert">{error}</div>}<div className="table">{requests.length === 0 ? <p>No requests found.</p> : requests.map(r => <article key={r.id}><div><b>{r.subject}</b><span>{r.category} · {r.priority}</span></div><em>{r.status}</em></article>)}</div></section></section></main>;
}

createRoot(document.getElementById('root')).render(<App />);
