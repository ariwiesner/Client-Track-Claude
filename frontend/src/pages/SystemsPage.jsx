import { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';

function patternSummary(system) {
  if (system.title_pattern_type === 'regex') {
    return system.title_regex ? `רגקס: ${system.title_regex}` : 'רגקס (לא הוגדר)';
  }
  if (system.title_delimiter) {
    return `מפריד "${system.title_delimiter}" · מקטע ${system.title_delimiter_index}`;
  }
  return 'זיהוי לפי שם המערכת בלבד';
}

export function SystemsPage() {
  const [systems, setSystems] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      setSystems(await api.listSystems());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleStopWatching(system) {
    if (!window.confirm(`להפסיק לעקוב אחרי "${system.name}"? העוזר האוטומטי יפסיק לזהות אותה.`)) return;
    await api.deleteSystem(system.id);
    load();
  }

  return (
    <div className="dashboard-page">
      <header className="dashboard-header">
        <div className="dashboard-header-text">
          <h1>מערכות</h1>
          <p className="muted">כל המערכות שהעוזר האוטומטי עוקב אחריהן</p>
        </div>
        <div className="header-actions">
          <Link to="/systems/new" className="add-fab" title="הוספת מערכת" aria-label="הוספת מערכת">
            <span style={{ fontSize: '1.3rem', lineHeight: 1 }}>+</span>
          </Link>
        </div>
      </header>

      {error && <p className="error">{error}</p>}

      {!loading && systems.length === 0 && (
        <p className="hint">עדיין לא נוספו מערכות למעקב — הוסיפו אחת כדי שהעוזר יזהה אותה.</p>
      )}

      <div className="client-grid">
        {systems.map((system) => (
          <div key={system.id} className="client-card" style={{ cursor: 'default' }}>
            <div className="client-card-header" style={{ paddingLeft: 0 }}>
              <div className="client-card-identity">
                <h3>{system.name}</h3>
                <p>{system.process_name ? `תהליך: ${system.process_name}` : 'כל תהליך'}</p>
                <p>{patternSummary(system)}</p>
              </div>
            </div>

            <div className="client-card-footer">
              <Link to={`/systems/${system.id}/edit`} className="button secondary">
                עריכה
              </Link>
              <button className="paid-toggle" onClick={() => handleStopWatching(system)}>
                הפסקת מעקב
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
