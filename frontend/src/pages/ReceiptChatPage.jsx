import { useState, useEffect, useRef } from 'react';
import { api } from '../api/client';

const CATEGORY_OPTIONS = [
  { value: 'food', label: 'מזון' },
  { value: 'office_supplies', label: 'ציוד משרדי' },
  { value: 'travel', label: 'נסיעות' },
  { value: 'business', label: 'עבור העסק' },
  { value: 'other', label: 'אחר' },
];

function UploadIcon() {
  return (
    <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <path d="M12 16V4M12 4l-4 4M12 4l4 4" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function WarningIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M12 3.5 21.5 20h-19L12 3.5Z" strokeLinejoin="round" />
      <path d="M12 9.5v5" strokeLinecap="round" />
      <circle cx="12" cy="17.2" r="0.9" fill="currentColor" stroke="none" />
    </svg>
  );
}

function FileIcon() {
  return (
    <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
      <path d="M6 3h8l5 5v13a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z" strokeLinejoin="round" />
      <path d="M14 3v5h5" strokeLinejoin="round" />
    </svg>
  );
}

function isPdfUrl(url) {
  return typeof url === 'string' && url.toLowerCase().split('?')[0].endsWith('.pdf');
}

function Thumbnail({ src }) {
  if (isPdfUrl(src)) {
    return (
      <a href={src} target="_blank" rel="noopener noreferrer" className="chat-pdf-thumb">
        <FileIcon />
        <span>צפייה ב-PDF</span>
      </a>
    );
  }
  return <img src={src} alt="קבלה" className="chat-thumb" />;
}

function buildForm(extraction) {
  return {
    client: extraction?.client_id ? String(extraction.client_id) : '',
    amount: extraction?.amount || '',
    receipt_number: extraction?.receipt_number || '',
    receipt_date: extraction?.receipt_date || new Date().toISOString().slice(0, 10),
    category: extraction?.category || 'other',
  };
}

function withForm(row) {
  return { ...row, form: row.status === 'pending' ? buildForm(row.extraction) : null };
}

export function ReceiptChatPage() {
  const [clients, setClients] = useState([]);
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState('');
  const scrollRef = useRef(null);

  useEffect(() => {
    api.listClients().then(setClients);
    api
      .listReceiptChat()
      .then((rows) => setEntries(rows.map(withForm)))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [entries, uploading]);

  function replaceEntry(id, updatedRow) {
    setEntries((prev) => prev.map((e) => (e.id === id ? withForm(updatedRow) : e)));
  }

  function updateField(id, field, value) {
    setEntries((prev) =>
      prev.map((e) =>
        e.id === id ? { ...e, form: { ...e.form, [field]: value }, duplicateWarning: null } : e
      )
    );
  }

  function clearDuplicateWarning(id) {
    setEntries((prev) => prev.map((e) => (e.id === id ? { ...e, duplicateWarning: null } : e)));
  }

  async function handleFileSelect(e) {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    setError('');
    setUploading(true);
    try {
      const row = await api.uploadReceiptChat(file);
      setEntries((prev) => [...prev, withForm(row)]);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  }

  async function handleApprove(entry, force = false) {
    setBusyId(entry.id);
    setError('');
    try {
      const updated = await api.approveReceiptChat(entry.id, { ...entry.form, force });
      replaceEntry(entry.id, updated);
    } catch (err) {
      if (err.status === 409 && err.data?.existing_receipt) {
        setEntries((prev) =>
          prev.map((e) => (e.id === entry.id ? { ...e, duplicateWarning: err.data.existing_receipt } : e))
        );
      } else {
        setError(err.message);
      }
    } finally {
      setBusyId(null);
    }
  }

  async function handleDiscard(entry) {
    setBusyId(entry.id);
    setError('');
    try {
      const updated = await api.discardReceiptChat(entry.id);
      replaceEntry(entry.id, updated);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  async function handleRetry(entry) {
    setBusyId(entry.id);
    setError('');
    try {
      const updated = await api.retryReceiptChat(entry.id);
      replaceEntry(entry.id, updated);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  async function handleResolvePages(entry, split) {
    setBusyId(entry.id);
    setError('');
    try {
      const { entries: resolved } = await api.resolveReceiptChatPages(entry.id, split);
      setEntries((prev) => {
        const index = prev.findIndex((e) => e.id === entry.id);
        if (index === -1) return prev;
        return [...prev.slice(0, index), ...resolved.map(withForm), ...prev.slice(index + 1)];
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="chat-page">
      <p className="hint chat-intro">
        העלו תמונה של קבלה — הבינה המלאכותית תזהה את הלקוח, הסכום והקטגוריה, ותציג לכם לאישור.
        היסטוריית הצ'אט נשמרת למשך 7 ימים.
      </p>

      {error && <p className="error">{error}</p>}

      <div className="chat-scroll">
        {loading && <p className="hint">טוען היסטוריה…</p>}

        {entries.map((entry) => (
          <ChatEntry
            key={entry.id}
            entry={entry}
            clients={clients}
            busy={busyId === entry.id}
            onFieldChange={(field, value) => updateField(entry.id, field, value)}
            onApprove={() => handleApprove(entry)}
            onForceApprove={() => handleApprove(entry, true)}
            onDismissWarning={() => clearDuplicateWarning(entry.id)}
            onDiscard={() => handleDiscard(entry)}
            onRetry={() => handleRetry(entry)}
            onResolvePages={(split) => handleResolvePages(entry, split)}
          />
        ))}

        {uploading && <div className="chat-bubble assistant loading">קורא את הקבלה…</div>}

        <div ref={scrollRef} />
      </div>

      <div className="chat-upload-zone">
        <input
          type="file"
          accept="image/*,application/pdf"
          capture="environment"
          onChange={handleFileSelect}
          className="chat-file-input"
          id="receipt-upload-input"
          disabled={uploading}
        />
        <label htmlFor="receipt-upload-input" className="button chat-upload-button">
          <UploadIcon />
          העלאת קבלה (תמונה או PDF)
        </label>
      </div>
    </div>
  );
}

function ChatEntry({
  entry,
  clients,
  busy,
  onFieldChange,
  onApprove,
  onForceApprove,
  onDismissWarning,
  onDiscard,
  onRetry,
  onResolvePages,
}) {
  if (entry.status === 'awaiting_page_choice') {
    return (
      <div className="chat-bubble assistant">
        <div className="card chat-review-card">
          <Thumbnail src={entry.image} />
          <p>
            הקובץ שהעליתם מכיל {entry.page_count} עמודים. האם מדובר בכמה קבלות נפרדות,
            או בקבלה אחת שמשתרעת על פני כמה עמודים?
          </p>
          <div className="chat-review-actions">
            <button className="secondary" onClick={() => onResolvePages(false)} disabled={busy}>
              {busy ? 'מעבד…' : 'קבלה אחת'}
            </button>
            <button onClick={() => onResolvePages(true)} disabled={busy}>
              {busy ? 'מעבד…' : `${entry.page_count} קבלות נפרדות`}
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (entry.status === 'error') {
    return (
      <div className="chat-bubble assistant error">
        <div className="card chat-review-card">
          <Thumbnail src={entry.image} />
          <p className="error">{entry.error_message}</p>
          <button className="secondary" onClick={onRetry} disabled={busy}>
            {busy ? 'מנסה…' : 'נסה שוב'}
          </button>
        </div>
      </div>
    );
  }

  if (entry.status === 'approved') {
    const { receipt } = entry;
    return (
      <div className="chat-bubble assistant">
        <div className="card chat-review-card">
          <Thumbnail src={entry.image} />
          <p className="success">
            ✓ נשמר עבור {receipt.client_name} — {receipt.category_display} — ₪
            {Number(receipt.amount).toFixed(2)}
          </p>
        </div>
      </div>
    );
  }

  if (entry.status === 'discarded') {
    return (
      <div className="chat-bubble assistant">
        <div className="card chat-review-card">
          <Thumbnail src={entry.image} />
          <p className="hint">בוטל.</p>
        </div>
      </div>
    );
  }

  // pending — editable review card
  const { form } = entry;
  const canApprove = form.client && form.amount && form.category && form.receipt_date;

  return (
    <div className="chat-bubble assistant">
      <div className="card chat-review-card">
        <Thumbnail src={entry.image} />

        <label>
          לקוח
          <select value={form.client} onChange={(e) => onFieldChange('client', e.target.value)}>
            <option value="">— בחירת לקוח —</option>
            {clients.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
        {form.client && entry.extraction?.client_match_score != null && (
          <p className="hint">זוהה אוטומטית ({Math.round(entry.extraction.client_match_score)}%)</p>
        )}
        {!form.client && entry.extraction?.client_suggestion && (
          <p className="error">
            לא נמצא לקוח מתאים בוודאות. הקרוב ביותר: "{entry.extraction.client_suggestion.name}"
            {' '}
            <button
              type="button"
              className="link-button"
              onClick={() => onFieldChange('client', String(entry.extraction.client_suggestion.client_id))}
            >
              בחירה
            </button>
          </p>
        )}
        {!form.client && !entry.extraction?.client_suggestion && (
          <p className="error">לא זוהה לקוח — יש לבחור ידנית.</p>
        )}

        <label>
          סכום (₪)
          <input
            type="number"
            step="0.01"
            min="0"
            value={form.amount}
            onChange={(e) => onFieldChange('amount', e.target.value)}
          />
        </label>
        <label>
          מספר קבלה
          <input
            type="text"
            value={form.receipt_number}
            onChange={(e) => onFieldChange('receipt_number', e.target.value)}
          />
        </label>
        <label>
          תאריך
          <input
            type="date"
            value={form.receipt_date}
            onChange={(e) => onFieldChange('receipt_date', e.target.value)}
          />
        </label>
        <label>
          קטגוריה
          <select value={form.category} onChange={(e) => onFieldChange('category', e.target.value)}>
            {CATEGORY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>

        {entry.duplicateWarning ? (
          <div className="duplicate-warning">
            <p className="error">
              <WarningIcon /> קבלה עם אותם פרטים כבר קיימת עבור לקוח זה — מספר קבלה{' '}
              {entry.duplicateWarning.receipt_number || '—'}, ₪
              {Number(entry.duplicateWarning.amount).toFixed(2)},{' '}
              {new Date(entry.duplicateWarning.receipt_date).toLocaleDateString('he-IL')}.
            </p>
            <div className="chat-review-actions">
              <button className="secondary" onClick={onDismissWarning} disabled={busy}>
                ביטול
              </button>
              <button className="danger" onClick={onForceApprove} disabled={busy}>
                <WarningIcon /> {busy ? 'שומר…' : 'הוסף בכל זאת'}
              </button>
            </div>
          </div>
        ) : (
          <div className="chat-review-actions">
            <button className="secondary" onClick={onDiscard} disabled={busy}>
              ביטול
            </button>
            <button onClick={onApprove} disabled={!canApprove || busy}>
              {busy ? 'שומר…' : 'אישור והוספה'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
