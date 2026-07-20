import { useState, useEffect } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { api } from '../api/client';

const emptyForm = {
  name: '',
  job_type: '',
  phone: '',
  contact_person: '',
  notes: '',
  hourly_rate: '',
  case_number: '',
  tax_subject: '',
  unit: '',
  sub_case: '',
  representative: '',
  representation_start: '',
  validity_91: '',
  bank_details: '',
};

export function ClientFormPage() {
  const { id } = useParams();
  const isEdit = !!id;
  const navigate = useNavigate();
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (isEdit) {
      api.getClient(id).then((client) => setForm(client));
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
        await api.updateClient(id, form);
        navigate(`/clients/${id}`);
      } else {
        await api.createClient(form);
        navigate('/');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="form-page">
      <h1>{isEdit ? 'עריכת לקוח' : 'הוספת לקוח'}</h1>
      <form onSubmit={handleSubmit}>
        <label>
          שם
          <input required value={form.name} onChange={(e) => update('name', e.target.value)} />
        </label>
        <label>
          תפקיד / סוג עבודה
          <input value={form.job_type} onChange={(e) => update('job_type', e.target.value)} />
        </label>
        <label>
          טלפון
          <input value={form.phone} onChange={(e) => update('phone', e.target.value)} />
        </label>
        <label>
          איש קשר
          <input
            value={form.contact_person}
            onChange={(e) => update('contact_person', e.target.value)}
          />
        </label>
        <label>
          תעריף לשעה (₪)
          <input
            required
            type="number"
            step="0.01"
            value={form.hourly_rate}
            onChange={(e) => update('hourly_rate', e.target.value)}
          />
        </label>
        <label>
          מספר תיק
          <input value={form.case_number} onChange={(e) => update('case_number', e.target.value)} />
        </label>
        <label>
          נושא מס
          <input value={form.tax_subject} onChange={(e) => update('tax_subject', e.target.value)} />
        </label>
        <label>
          חוליה
          <input value={form.unit} onChange={(e) => update('unit', e.target.value)} />
        </label>
        <label>
          ס.תיק
          <input value={form.sub_case} onChange={(e) => update('sub_case', e.target.value)} />
        </label>
        <label>
          מייצג
          <input
            value={form.representative}
            onChange={(e) => update('representative', e.target.value)}
          />
        </label>
        <label>
          תחילת ייצוג
          <input value={form.representation_start} readOnly disabled />
        </label>
        <label>
          תוקף 91
          <input value={form.validity_91} onChange={(e) => update('validity_91', e.target.value)} />
        </label>
        <label>
          פרטי בנק
          <input value={form.bank_details} onChange={(e) => update('bank_details', e.target.value)} />
        </label>
        <label>
          הערות
          <textarea value={form.notes} onChange={(e) => update('notes', e.target.value)} />
        </label>

        {error && <p className="error">{error}</p>}

        <div className="form-actions">
          <button type="submit" disabled={submitting}>
            {isEdit ? 'שמירה' : 'הוספת לקוח'}
          </button>
          <Link to={isEdit ? `/clients/${id}` : '/'} className="button secondary">
            ביטול
          </Link>
        </div>
      </form>
    </div>
  );
}
