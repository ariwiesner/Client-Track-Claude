import { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';

export function ProfilePage() {
  const { user } = useAuth();
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState('');
  const [passwordForm, setPasswordForm] = useState({ old_password: '', new_password: '' });
  const [passwordError, setPasswordError] = useState('');
  const [passwordSuccess, setPasswordSuccess] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const now = new Date();

  const load = useCallback(async () => {
    try {
      setSummary(await api.getMySummary(now.getFullYear(), now.getMonth() + 1));
    } catch (err) {
      setError(err.message);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function updatePasswordField(field, value) {
    setPasswordForm((f) => ({ ...f, [field]: value }));
  }

  async function handlePasswordSubmit(e) {
    e.preventDefault();
    setPasswordError('');
    setPasswordSuccess('');
    setSubmitting(true);
    try {
      await api.changePassword(passwordForm);
      setPasswordSuccess('הסיסמה עודכנה בהצלחה.');
      setPasswordForm({ old_password: '', new_password: '' });
    } catch (err) {
      setPasswordError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="form-page">
      <h1>הפרופיל שלי</h1>

      {error && <p className="error">{error}</p>}

      {summary && (
        <section className="card">
          <h2>החודש שלי</h2>
          <div className="stat-bar">
            <div className="stat-bar-stats">
              <div className="stat-tile">
                <span className="stat-label">סה"כ שעות</span>
                <span className="stat-value mono">{summary.total_hours.toFixed(2)}</span>
              </div>
              <div className="stat-tile">
                <span className="stat-label">מקום במשרד</span>
                <span className="stat-value mono">
                  {summary.rank ? `#${summary.rank} מתוך ${summary.total_workers}` : '—'}
                </span>
              </div>
            </div>
          </div>

          {summary.breakdown.length > 0 ? (
            <div className="breakdown" style={{ marginTop: 'var(--space-4)' }}>
              <h3 className="breakdown-title">פילוח לפי לקוח ומערכת</h3>
              <ul className="breakdown-list">
                {summary.breakdown.map((row) => (
                  <li key={`${row.client_id}-${row.system_name}`}>
                    <span>
                      <Link to={`/clients/${row.client_id}`}>{row.client_name}</Link>
                      {' · '}
                      {row.system_name}
                    </span>
                    <span>{row.hours.toFixed(2)} שעות</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="hint">טרם נרשמו שעות החודש.</p>
          )}
        </section>
      )}

      <section className="card">
        <h2>שינוי סיסמה</h2>
        <form onSubmit={handlePasswordSubmit}>
          <label>
            סיסמה נוכחית
            <input
              required
              type="password"
              value={passwordForm.old_password}
              onChange={(e) => updatePasswordField('old_password', e.target.value)}
            />
          </label>
          <label>
            סיסמה חדשה
            <input
              required
              type="password"
              minLength={4}
              value={passwordForm.new_password}
              onChange={(e) => updatePasswordField('new_password', e.target.value)}
            />
          </label>

          {passwordError && <p className="error">{passwordError}</p>}
          {passwordSuccess && <p className="success">{passwordSuccess}</p>}

          <div className="form-actions">
            <button type="submit" disabled={submitting}>
              {submitting ? 'שומר…' : 'עדכון סיסמה'}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
