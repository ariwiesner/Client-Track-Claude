import { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { api } from '../api/client';
import { groupHoursBySystem } from '../utils/breakdown';

function whatsAppLink(phone) {
  if (!phone) return null;
  let digits = phone.replace(/\D/g, '');
  if (!digits) return null;
  if (digits.startsWith('0')) {
    digits = '972' + digits.slice(1); // מספר ישראלי מקומי -> בינלאומי
  }
  return `https://wa.me/${digits}`;
}

function WhatsAppIcon() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" fill="#25D366" aria-hidden="true">
      <path d="M12.001 2.003c-5.514 0-9.997 4.483-9.997 9.997 0 1.762.464 3.484 1.346 4.997L2 22l5.129-1.345a9.96 9.96 0 0 0 4.872 1.242h.005c5.514 0 9.997-4.483 9.997-9.997 0-2.67-1.04-5.18-2.929-7.069a9.935 9.935 0 0 0-7.073-2.925zm.004 18.11h-.004a8.17 8.17 0 0 1-4.164-1.14l-.299-.177-3.098.812.827-3.023-.194-.31a8.16 8.16 0 0 1-1.257-4.35c0-4.516 3.674-8.19 8.19-8.19a8.14 8.14 0 0 1 5.795 2.398 8.14 8.14 0 0 1 2.395 5.796c0 4.516-3.674 8.184-8.191 8.184z" />
      <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z" />
    </svg>
  );
}

const SOURCE_LABELS = { manual: 'ידני', auto: 'אוטומטי' };
const STATUS_LABELS = { running: 'פעיל', stopped: 'הסתיים', cancelled: 'בוטל' };

function ChevronIcon({ direction }) {
  const d = direction === 'next' ? 'M9 6l6 6-6 6' : 'M15 6l-6 6 6 6';
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d={d} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function ClientDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [client, setClient] = useState(null);
  const [billing, setBilling] = useState(null);
  const [entries, setEntries] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const today = new Date();
  const [viewYear, setViewYear] = useState(today.getFullYear());
  const [viewMonth, setViewMonth] = useState(today.getMonth()); // 0-indexed
  const isCurrentMonth = viewYear === today.getFullYear() && viewMonth === today.getMonth();

  function goToPrevMonth() {
    setViewMonth((m) => {
      if (m === 0) {
        setViewYear((y) => y - 1);
        return 11;
      }
      return m - 1;
    });
  }

  function goToNextMonth() {
    setViewMonth((m) => {
      if (m === 11) {
        setViewYear((y) => y + 1);
        return 0;
      }
      return m + 1;
    });
  }

  const monthLabel = new Date(viewYear, viewMonth, 1).toLocaleString('he-IL', {
    month: 'long',
    year: 'numeric',
  });

  const load = useCallback(async () => {
    try {
      const [clientData, billingRows, entriesData] = await Promise.all([
        api.getClient(id),
        api.listBilling(viewYear, viewMonth + 1, id),
        api.listTimeEntriesForClient(id),
      ]);
      setClient(clientData);
      setBilling(billingRows.find((row) => String(row.client.id) === String(id)) || null);
      setEntries(entriesData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [id, viewYear, viewMonth]);

  useEffect(() => {
    load();
  }, [load]);

  const breakdown = useMemo(() => {
    return groupHoursBySystem(entries, viewYear, viewMonth);
  }, [entries, viewYear, viewMonth]);

  async function handleTogglePaid() {
    if (!billing) return;
    await api.togglePaid(billing.id);
    load();
  }

  async function handleDeactivate() {
    if (!client) return;
    if (!window.confirm(`להשבית את ${client.name}? הלקוח יוסתר מלוח הבקרה.`)) return;
    await api.deleteClient(id);
    navigate('/');
  }

  if (loading) return <p className="hint">טוען…</p>;
  if (error) return <p className="error">{error}</p>;
  if (!client) return <p className="error">הלקוח לא נמצא.</p>;

  return (
    <div className="detail-page">
      <section className="card">
        <div className="detail-header">
          <div>
            <h1>{client.name}</h1>
            {client.job_type && <p className="muted">{client.job_type}</p>}
          </div>
          <div className="detail-header-actions">
            <Link to={`/manual-entry?client=${client.id}`} className="button secondary">
              רישום שעות
            </Link>
            <Link to={`/clients/${client.id}/edit`} className="button">
              עריכה
            </Link>
          </div>
        </div>

        <dl className="detail-list">
          <div>
            <dt>טלפון</dt>
            <dd>{client.phone || '—'}</dd>
          </div>
          <div>
            <dt>איש קשר</dt>
            <dd>{client.contact_person || '—'}</dd>
          </div>
          <div>
            <dt>תעריף לשעה</dt>
            <dd>₪{Number(client.hourly_rate).toFixed(2)}</dd>
          </div>
          <div>
            <dt>הערות</dt>
            <dd>{client.notes || '—'}</dd>
          </div>
          <div>
            <dt>מספר תיק</dt>
            <dd>{client.case_number || '—'}</dd>
          </div>
          <div>
            <dt>נושא מס</dt>
            <dd>{client.tax_subject || '—'}</dd>
          </div>
          <div>
            <dt>חוליה</dt>
            <dd>{client.unit || '—'}</dd>
          </div>
          <div>
            <dt>ס.תיק</dt>
            <dd>{client.sub_case || '—'}</dd>
          </div>
          <div>
            <dt>מייצג</dt>
            <dd>{client.representative || '—'}</dd>
          </div>
          <div>
            <dt>תחילת ייצוג</dt>
            <dd>{client.representation_start || '—'}</dd>
          </div>
          <div>
            <dt>תוקף 91</dt>
            <dd>{client.validity_91 || '—'}</dd>
          </div>
          <div>
            <dt>פרטי בנק</dt>
            <dd>{client.bank_details || '—'}</dd>
          </div>
        </dl>
        <div className="details-footer">
          <button className="danger" onClick={handleDeactivate}>
            השבתת לקוח
          </button>
          {whatsAppLink(client.phone) && (
            <a
              href={whatsAppLink(client.phone)}
              target="_blank"
              rel="noopener noreferrer"
              className="icon-nav-button whatsapp-button"
              title="פתיחת שיחת וואטסאפ"
              aria-label={`שליחת הודעה ל${client.name} בוואטסאפ`}
            >
              <WhatsAppIcon />
            </a>
          )}
        </div>
      </section>

      <section className="card">
        <div className="detail-header">
          <h2 style={{ marginBottom: 0 }}>החודש</h2>
          <div className="month-nav">
            <button className="icon-nav-button" onClick={goToPrevMonth} title="החודש הקודם" aria-label="החודש הקודם">
              <ChevronIcon direction="prev" />
            </button>
            <span className="month-nav-label">{monthLabel}</span>
            <button className="icon-nav-button" onClick={goToNextMonth} title="החודש הבא" aria-label="החודש הבא">
              <ChevronIcon direction="next" />
            </button>
            {!isCurrentMonth && (
              <button
                className="button secondary month-nav-today"
                onClick={() => {
                  setViewYear(today.getFullYear());
                  setViewMonth(today.getMonth());
                }}
              >
                חזרה להיום
              </button>
            )}
          </div>
        </div>

        {billing ? (
          <div className="stat-bar">
            <div className="stat-bar-stats">
              <div className="stat-tile">
                <span className="stat-label">שעות החודש</span>
                <span className="stat-value mono">{Number(billing.total_hours).toFixed(2)}</span>
              </div>
              <div className="stat-tile">
                <span className="stat-label">סכום לתשלום</span>
                <span className="stat-value mono">₪{Number(billing.amount_owed).toFixed(2)}</span>
              </div>
              <div className="stat-tile">
                <span className="stat-label">סטטוס</span>
                <span className={`status-pill ${billing.paid ? 'paid' : 'unpaid'}`}>
                  {billing.paid ? 'שולם' : 'לא שולם'}
                </span>
              </div>
            </div>
            <button onClick={handleTogglePaid}>סמן כ{billing.paid ? 'לא שולם' : 'שולם'}</button>
          </div>
        ) : (
          <p className="hint">אין נתוני חיוב לחודש זה.</p>
        )}

        {breakdown.length > 0 && (
          <div className="breakdown">
            <h3 className="breakdown-title">פילוח שעות</h3>
            <ul className="breakdown-list">
              {breakdown.map(([label, hours]) => (
                <li key={label}>
                  <span>{label}</span>
                  <span>{hours.toFixed(2)} שעות</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>

      <section className="card">
        <h2>רישומי זמן אחרונים</h2>
        {entries.length === 0 ? (
          <p className="hint">טרם נרשמו רישומי זמן.</p>
        ) : (
          <div className="table-scroll">
            <table className="entries-table">
              <thead>
                <tr>
                  <th>תאריך</th>
                  <th>עובד</th>
                  <th>מערכת</th>
                  <th>משך</th>
                  <th>מקור</th>
                  <th>סטטוס</th>
                </tr>
              </thead>
              <tbody>
                {entries.slice(0, 25).map((entry) => (
                  <tr key={entry.id}>
                    <td>{new Date(entry.start_time).toLocaleDateString('he-IL')}</td>
                    <td>{entry.employee.first_name || entry.employee.username}</td>
                    <td>{entry.system_name || 'ידני'}</td>
                    <td>{Number(entry.duration_hours).toFixed(2)} שעות</td>
                    <td>{SOURCE_LABELS[entry.source] || entry.source}</td>
                    <td>{STATUS_LABELS[entry.status] || entry.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
