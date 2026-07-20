import { useState, useEffect } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { api } from '../api/client';

const emptyForm = {
  name: '',
  process_name: '',
  title_pattern_type: 'delimiter',
  title_delimiter: '',
  title_delimiter_index: 0,
  title_regex: '',
};

export function SystemFormPage() {
  const { id } = useParams();
  const isEdit = !!id;
  const navigate = useNavigate();
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  useEffect(() => {
    if (isEdit) {
      api.listSystems().then((systems) => {
        const found = systems.find((s) => String(s.id) === id);
        if (found) {
          setForm(found);
          if (found.process_name || found.title_delimiter || found.title_regex) {
            setShowAdvanced(true);
          }
        }
      });
    }
  }, [id, isEdit]);

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      if (isEdit) {
        await api.updateSystem(id, form);
      } else {
        await api.createSystem(form);
      }
      navigate('/');
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="form-page">
      <h1>{isEdit ? 'עריכת מערכת' : 'הוספת מערכת'}</h1>
      <p className="hint">
        התוכנה שרצה ברקע עוקבת אחר הופעת השם הזה בכותרת של כל חלון פתוח —
        גם כרטיסייה בדפדפן (כרום, אדג׳...) וגם תוכנה עצמאית עובדות, למשל "Google Translate"
        או "Netflix". כשהמערכת פתוחה, תופיע שאלה האם להתחיל למדוד זמן עבורה.
      </p>
      <form onSubmit={handleSubmit}>
        <label>
          שם המערכת
          <input
            required
            value={form.name}
            onChange={(e) => update('name', e.target.value)}
            placeholder="למשל Google Translate, Netflix, חשבשבת"
          />
        </label>

        <button
          type="button"
          className="button secondary"
          onClick={() => setShowAdvanced((v) => !v)}
        >
          {showAdvanced ? 'הסתרת אפשרויות מתקדמות' : 'הצגת אפשרויות מתקדמות'}
        </button>

        {showAdvanced && (
          <>
            <p className="hint">
              נדרש רק עבור תוכנה שכותבת את שם הלקוח לתוך כותרת החלון שלה ברגע שבוחרים
              אותו (למשל תוכנת הנהלת חשבונות שמציגה "שם לקוח - חשבשבת"). השאירו ריק
              עבור דברים כמו Google Translate או Netflix.
            </p>
            <label>
              שם קובץ ההרצה (אופציונלי — מגביל את הזיהוי לתהליך הזה)
              <input
                value={form.process_name}
                onChange={(e) => update('process_name', e.target.value)}
                placeholder="למשל hashav.exe"
              />
            </label>
            <label>
              שיטת חילוץ הכותרת
              <select
                value={form.title_pattern_type}
                onChange={(e) => update('title_pattern_type', e.target.value)}
              >
                <option value="delimiter">פיצול לפי מפריד</option>
                <option value="regex">ביטוי רגולרי (מתקדם)</option>
              </select>
            </label>

            {form.title_pattern_type === 'delimiter' ? (
              <>
                <label>
                  מפריד (למשל " - ")
                  <input
                    value={form.title_delimiter}
                    onChange={(e) => update('title_delimiter', e.target.value)}
                  />
                </label>
                <label>
                  מיקום המקטע עם שם הלקוח (0 = הראשון)
                  <input
                    type="number"
                    min="0"
                    value={form.title_delimiter_index}
                    onChange={(e) => update('title_delimiter_index', Number(e.target.value))}
                  />
                </label>
              </>
            ) : (
              <label>
                ביטוי רגולרי (חייב לכלול קבוצה בשם "client")
                <input
                  value={form.title_regex}
                  onChange={(e) => update('title_regex', e.target.value)}
                  placeholder="^(?P<client>.+?) - Hashav$"
                />
              </label>
            )}
          </>
        )}

        {error && <p className="error">{error}</p>}

        <div className="form-actions">
          <button type="submit" disabled={submitting}>
            {isEdit ? 'שמירה' : 'הוספת מערכת'}
          </button>
          <Link to="/" className="button secondary">ביטול</Link>
        </div>
      </form>
    </div>
  );
}
