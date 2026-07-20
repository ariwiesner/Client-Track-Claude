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

export function ReceiptChatPage() {
  const [clients, setClients] = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [pending, setPending] = useState(null);
  const [status, setStatus] = useState('idle'); // idle | extracting | approving
  const fileInputRef = useRef(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    api.listClients().then(setClients);
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [timeline, pending]);

  function addLine(entry) {
    setTimeline((t) => [...t, { id: Date.now() + Math.random(), ...entry }]);
  }

  async function runExtraction(file) {
    setStatus('extracting');
    try {
      const result = await api.extractReceipt(file);
      setPending({
        imageFile: file,
        previewUrl: URL.createObjectURL(file),
        matchScore: result.client_match_score,
        clientNameGuess: result.client_name_guess,
        form: {
          client: result.client_id ? String(result.client_id) : '',
          amount: result.amount || '',
          receipt_number: result.receipt_number || '',
          receipt_date: result.receipt_date || new Date().toISOString().slice(0, 10),
          category: result.category || 'other',
        },
      });
      setStatus('idle');
    } catch (err) {
      addLine({ kind: 'error', message: err.message, file });
      setStatus('idle');
    }
  }

  function handleFileSelect(e) {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    addLine({ kind: 'upload', previewUrl: URL.createObjectURL(file) });
    runExtraction(file);
  }

  function updateField(field, value) {
    setPending((p) => ({ ...p, form: { ...p.form, [field]: value } }));
  }

  async function handleApprove() {
    if (!pending) return;
    setStatus('approving');
    try {
      const receipt = await api.createReceipt(pending.form, pending.imageFile);
      const client = clients.find((c) => String(c.id) === String(receipt.client));
      addLine({ kind: 'success', clientName: client?.name || receipt.client_name });
      setPending(null);
    } catch (err) {
      addLine({ kind: 'error', message: err.message });
    } finally {
      setStatus('idle');
    }
  }

  function handleDiscard() {
    addLine({ kind: 'discarded' });
    setPending(null);
  }

  function handleRetry(file) {
    runExtraction(file);
  }

  const canApprove =
    pending &&
    pending.form.client &&
    pending.form.amount &&
    pending.form.category &&
    pending.form.receipt_date;

  return (
    <div className="chat-page">
      <p className="hint chat-intro">
        העלו תמונה של קבלה — הבינה המלאכותית תזהה את הלקוח, הסכום והקטגוריה, ותציג לכם לאישור.
      </p>

      <div className="chat-scroll">
        {timeline.map((line) => (
          <ChatLine key={line.id} line={line} onRetry={handleRetry} />
        ))}

        {status === 'extracting' && (
          <div className="chat-bubble assistant loading">קורא את הקבלה…</div>
        )}

        {pending && (
          <div className="chat-bubble assistant">
            <div className="card chat-review-card">
              <img src={pending.previewUrl} alt="תצוגה מקדימה של הקבלה" className="chat-thumb" />

              <label>
                לקוח
                <select value={pending.form.client} onChange={(e) => updateField('client', e.target.value)}>
                  <option value="">— בחירת לקוח —</option>
                  {clients.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </label>
              {pending.form.client && pending.matchScore != null && (
                <p className="hint">זוהה אוטומטית ({Math.round(pending.matchScore)}%)</p>
              )}
              {!pending.form.client && pending.clientNameGuess && (
                <p className="error">
                  לא זוהה לקוח בוודאות (נראה כמו "{pending.clientNameGuess}") — יש לבחור ידנית.
                </p>
              )}
              {!pending.form.client && !pending.clientNameGuess && (
                <p className="error">לא זוהה לקוח — יש לבחור ידנית.</p>
              )}

              <label>
                סכום (₪)
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={pending.form.amount}
                  onChange={(e) => updateField('amount', e.target.value)}
                />
              </label>
              <label>
                מספר קבלה
                <input
                  type="text"
                  value={pending.form.receipt_number}
                  onChange={(e) => updateField('receipt_number', e.target.value)}
                />
              </label>
              <label>
                תאריך
                <input
                  type="date"
                  value={pending.form.receipt_date}
                  onChange={(e) => updateField('receipt_date', e.target.value)}
                />
              </label>
              <label>
                קטגוריה
                <select value={pending.form.category} onChange={(e) => updateField('category', e.target.value)}>
                  {CATEGORY_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </label>

              <div className="chat-review-actions">
                <button className="secondary" onClick={handleDiscard} disabled={status === 'approving'}>
                  ביטול
                </button>
                <button onClick={handleApprove} disabled={!canApprove || status === 'approving'}>
                  {status === 'approving' ? 'שומר…' : 'אישור והוספה'}
                </button>
              </div>
            </div>
          </div>
        )}

        <div ref={scrollRef} />
      </div>

      <div className="chat-upload-zone">
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          onChange={handleFileSelect}
          className="chat-file-input"
          id="receipt-upload-input"
        />
        <label htmlFor="receipt-upload-input" className="button chat-upload-button">
          <UploadIcon />
          העלאת תמונת קבלה
        </label>
      </div>
    </div>
  );
}

function ChatLine({ line, onRetry }) {
  if (line.kind === 'upload') {
    return (
      <div className="chat-bubble user">
        <img src={line.previewUrl} alt="קבלה שהועלתה" className="chat-thumb" />
      </div>
    );
  }
  if (line.kind === 'success') {
    return (
      <div className="chat-bubble assistant">
        <p className="success">✓ הקבלה נשמרה עבור {line.clientName}</p>
      </div>
    );
  }
  if (line.kind === 'discarded') {
    return (
      <div className="chat-bubble assistant">
        <p className="hint">בוטל.</p>
      </div>
    );
  }
  if (line.kind === 'error') {
    return (
      <div className="chat-bubble assistant error">
        <p className="error">{line.message}</p>
        {line.file && (
          <button className="secondary" onClick={() => onRetry(line.file)}>
            נסה שוב
          </button>
        )}
      </div>
    );
  }
  return null;
}
