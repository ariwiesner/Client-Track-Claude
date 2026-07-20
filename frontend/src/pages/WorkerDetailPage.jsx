import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';

export function WorkerDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user: me } = useAuth();
  const [worker, setWorker] = useState(null);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const now = new Date();

  const load = useCallback(async () => {
    try {
      const [workerData, summaryData] = await Promise.all([
        api.getWorker(id),
        api.getWorkerSummary(id, now.getFullYear(), now.getMonth() + 1),
      ]);
      setWorker(workerData);
      setSummary(summaryData);
    } catch (err) {
      setError(err.message);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    if (!me?.is_staff) return;
    load();
  }, [me, load]);

  async function handleToggleAdmin() {
    if (!worker) return;
    setBusy(true);
    setError('');
    try {
      const updated = await api.updateWorker(id, { is_staff: !worker.is_staff });
      setWorker(updated);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete() {
    if (!worker) return;
    if (!window.confirm(`להשבית את ${worker.first_name || worker.username}? הוא לא יוכל להתחבר יותר.`)) return;
    setBusy(true);
    setError('');
    try {
      await api.deleteWorker(id);
      navigate('/workers');
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  if (!me?.is_staff) {
    return <p className="error">הדף הזה זמין רק למנהל המשרד.</p>;
  }

  if (error && !worker) return <p className="error">{error}</p>;
  if (!worker) return <p className="hint">טוען…</p>;

  const isSelf = String(me.id) === String(worker.id);

  return (
    <div className="detail-page">
      <section className="card">
        <div className="detail-header">
          <div>
            <h1>{worker.first_name || worker.username}</h1>
            <p className="muted">
              {worker.username}
              {worker.is_staff && ' · מנהל'}
              {worker.is_active === false && ' · מושבת'}
            </p>
          </div>
        </div>

        {error && <p className="error">{error}</p>}

        <div className="details-footer">
          <button onClick={handleToggleAdmin} disabled={busy || isSelf}>
            {worker.is_staff ? 'הסרת הרשאות מנהל' : 'הפיכה למנהל'}
          </button>
          <button className="danger" onClick={handleDelete} disabled={busy || isSelf || worker.is_active === false}>
            השבתת עובד
          </button>
        </div>
        {isSelf && <p className="hint">אי אפשר לשנות הרשאות או להשבית את עצמך.</p>}
      </section>

      {summary && (
        <section className="card">
          <h2>החודש</h2>
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
    </div>
  );
}
