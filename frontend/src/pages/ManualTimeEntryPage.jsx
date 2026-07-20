import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { api } from '../api/client';
import { useTimer } from '../context/TimerContext';

export function ManualTimeEntryPage() {
  const [searchParams] = useSearchParams();
  const [clients, setClients] = useState([]);
  const [selectedClient, setSelectedClient] = useState(searchParams.get('client') || '');
  const [error, setError] = useState('');

  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [hours, setHours] = useState('');
  const [logging, setLogging] = useState(false);
  const [logged, setLogged] = useState(false);

  const { entry, start } = useTimer();
  const navigate = useNavigate();

  useEffect(() => {
    api.listClients().then(setClients);
  }, []);

  async function handleStartLive() {
    setError('');
    try {
      await start(selectedClient, { source: 'manual' });
      navigate('/');
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleLogPastHours(e) {
    e.preventDefault();
    setError('');
    setLogging(true);
    setLogged(false);
    try {
      await api.logManualHours({ client_id: selectedClient, date, hours });
      setLogged(true);
      setHours('');
    } catch (err) {
      setError(err.message);
    } finally {
      setLogging(false);
    }
  }

  return (
    <div className="form-page">
      <h1>רישום שעות עבודה</h1>

      <label>
        לקוח
        <select value={selectedClient} onChange={(e) => setSelectedClient(e.target.value)}>
          <option value="">— בחירת לקוח —</option>
          {clients.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </label>

      {error && <p className="error">{error}</p>}

      <section className="manual-entry-section">
        <h2>הפעלת טיימר חי עכשיו</h2>
        <button onClick={handleStartLive} disabled={!selectedClient || !!entry}>
          {entry ? 'טיימר כבר פעיל' : 'הפעלת טיימר עבור לקוח זה'}
        </button>
      </section>

      <section className="manual-entry-section">
        <h2>רישום שעות עבור עבודה שבוצעה</h2>
        <form onSubmit={handleLogPastHours}>
          <label>
            תאריך
            <input type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
          </label>
          <label>
            שעות
            <input
              type="number"
              step="0.25"
              min="0"
              value={hours}
              onChange={(e) => setHours(e.target.value)}
              required
            />
          </label>
          <button type="submit" disabled={!selectedClient || logging}>
            {logging ? 'נרשם…' : 'רישום שעות'}
          </button>
        </form>
        {logged && <p className="success">השעות נרשמו.</p>}
      </section>
    </div>
  );
}
