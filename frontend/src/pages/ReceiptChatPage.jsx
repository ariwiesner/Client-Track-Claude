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
      prev.map((e) => (e.id === id ? { ...e, form: { ...e.form, [field]: value } } : e))
    );
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

  async function handleApprove(entry) {
    setBusyId(entry.id);
    setError('');
    try {
      const updated = await api.approveReceiptChat(entry.id, entry.form);
      replaceEntry(entry.id, updated);
    } catch (err) {
      setError(err.message);
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
            onDiscard={() => handleDiscard(entry)}
            onRetry={() => handleRetry(entry)}
          />
        ))}

        {uploading && <div className="chat-bubble assistant loading">קורא את הקבלה…</div>}

        <div ref={scrollRef} />
      </div>

      <div className="chat-upload-zone">
        <input
          type="file"
          accept="image/*"
          capture="environment"
          onChange={handleFileSelect}
          className="chat-file-input"
          id="receipt-upload-input"
          disabled={uploading}
        />
        <label htmlFor="receipt-upload-input" className="button chat-upload-button">
          <UploadIcon />
          העלאת תמונת קבלה
        </label>
      </div>
    </div>
  );
}

function ChatEntry({ entry, clients, busy, onFieldChange, onApprove, onDiscard, onRetry }) {
  if (entry.status === 'error') {
    return (
      <div className="chat-bubble assistant error">
        <div className="card chat-review-card">
          <img src={entry.image} alt="קבלה" className="chat-thumb" />
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
          <img src={entry.image} alt="קבלה" className="chat-thumb" />
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
          <img src={entry.image} alt="קבלה" className="chat-thumb" />
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
        <img src={entry.image} alt="קבלה" className="chat-thumb" />

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
        {!form.client && entry.extraction?.client_name_guess && (
          <p className="error">
            לא זוהה לקוח בוודאות (נראה כמו "{entry.extraction.client_name_guess}") — יש לבחור ידנית.
          </p>
        )}
        {!form.client && !entry.extraction?.client_name_guess && (
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

        <div className="chat-review-actions">
          <button className="secondary" onClick={onDiscard} disabled={busy}>
            ביטול
          </button>
          <button onClick={onApprove} disabled={!canApprove || busy}>
            {busy ? 'שומר…' : 'אישור והוספה'}
          </button>
        </div>
      </div>
    </div>
  );
}
