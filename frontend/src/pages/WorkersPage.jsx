import { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';

const emptyForm = { username: '', first_name: '', password: '' };

export function WorkersPage() {
  const { user } = useAuth();
  const [workers, setWorkers] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(async () => {
    try {
      setWorkers(await api.listWorkers());
    } catch (err) {
      setError(err.message);
    }
  }, []);

  useEffect(() => {
    if (user?.is_staff) load();
  }, [user, load]);

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setSuccess('');
    setSubmitting(true);
    try {
      await api.createWorker(form);
      setSuccess(`העובד ${form.first_name || form.username} נוסף בהצלחה.`);
      setForm(emptyForm);
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (!user?.is_staff) {
    return <p className="error">הדף הזה זמין רק למנהל המשרד.</p>;
  }

  return (
    <div className="form-page">
      <h1>עובדים</h1>

      <form onSubmit={handleSubmit}>
        <label>
          שם פרטי
          <input required value={form.first_name} onChange={(e) => update('first_name', e.target.value)} />
        </label>
        <label>
          שם משתמש
          <input
            required
            value={form.username}
            onChange={(e) => update('username', e.target.value)}
            autoCapitalize="off"
          />
        </label>
        <label>
          סיסמה זמנית
          <input
            required
            type="text"
            minLength={4}
            value={form.password}
            onChange={(e) => update('password', e.target.value)}
          />
        </label>

        {error && <p className="error">{error}</p>}
        {success && <p className="success">{success}</p>}

        <div className="form-actions">
          <button type="submit" disabled={submitting}>
            {submitting ? 'מוסיף…' : 'הוספת עובד'}
          </button>
        </div>
      </form>

      <h2 style={{ marginTop: 'var(--space-6)' }}>עובדים קיימים</h2>
      <ul className="breakdown-list">
        {workers.map((worker) => (
          <li key={worker.id}>
            <Link to={`/workers/${worker.id}`}>{worker.first_name || worker.username}</Link>
            <span className="mono">
              {worker.username}
              {worker.is_staff ? ' · מנהל' : ''}
              {worker.is_active === false ? ' · מושבת' : ''}
            </span>
          </li>
        ))}
      </ul>
      {workers.length === 0 && <p className="hint">אין עדיין עובדים רשומים.</p>}
    </div>
  );
}
