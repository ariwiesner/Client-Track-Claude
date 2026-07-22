import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';

function ChevronIcon({ direction }) {
  const d = direction === 'next' ? 'M9 6l6 6-6 6' : 'M15 6l-6 6 6 6';
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d={d} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

const WEEKDAY_LABELS = ['א', 'ב', 'ג', 'ד', 'ה', 'ו', 'ש'];
const REMINDER_PRESETS = [5, 15, 30, 60, 1440];
const emptyForm = { title: '', time: '10:00', reminder: '15', customReminder: '', notes: '' };

function pad(n) {
  return String(n).padStart(2, '0');
}
function isoDate(d) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}
function sameDay(a, b) {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

// Sunday-first 6-week grid (42 cells) covering the visible month plus the
// leading/trailing days from neighboring months needed to fill whole weeks.
function buildMonthGrid(year, month) {
  const firstOfMonth = new Date(year, month, 1);
  const gridStart = new Date(year, month, 1 - firstOfMonth.getDay());
  return Array.from({ length: 42 }, (_, i) => {
    const d = new Date(gridStart);
    d.setDate(gridStart.getDate() + i);
    return d;
  });
}

export function CalendarPage() {
  const { user } = useAuth();
  const isSuperuser = !!user?.is_superuser;
  const today = new Date();
  const [viewYear, setViewYear] = useState(today.getFullYear());
  const [viewMonth, setViewMonth] = useState(today.getMonth());
  const [meetings, setMeetings] = useState([]);
  const [error, setError] = useState('');
  const [popover, setPopover] = useState(null); // { day, meeting: meeting|null }
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const popoverRef = useRef(null);

  const days = useMemo(() => buildMonthGrid(viewYear, viewMonth), [viewYear, viewMonth]);
  const monthLabel = new Date(viewYear, viewMonth, 1).toLocaleString('he-IL', { month: 'long', year: 'numeric' });
  const isCurrentMonth = viewYear === today.getFullYear() && viewMonth === today.getMonth();

  const load = useCallback(async () => {
    try {
      setMeetings(await api.listMeetings(isoDate(days[0]), isoDate(days[days.length - 1])));
    } catch (err) {
      setError(err.message);
    }
  }, [days]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!popover) return;
    function onClick(e) {
      if (popoverRef.current && !popoverRef.current.contains(e.target)) setPopover(null);
    }
    function onKey(e) {
      if (e.key === 'Escape') setPopover(null);
    }
    document.addEventListener('mousedown', onClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [popover]);

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

  function meetingsForDay(day) {
    return meetings
      .filter((m) => sameDay(new Date(m.start_time), day))
      .sort((a, b) => new Date(a.start_time) - new Date(b.start_time));
  }

  function openCreate(day) {
    if (!isSuperuser) return;
    setError('');
    setForm(emptyForm);
    setPopover({ day, meeting: null });
  }

  function openMeeting(meeting, day) {
    if (!isSuperuser) {
      setPopover({ day, meeting });
      return;
    }
    const start = new Date(meeting.start_time);
    const isPreset = REMINDER_PRESETS.includes(meeting.reminder_minutes_before);
    setError('');
    setForm({
      title: meeting.title,
      time: `${pad(start.getHours())}:${pad(start.getMinutes())}`,
      reminder: isPreset ? String(meeting.reminder_minutes_before) : 'custom',
      customReminder: isPreset ? '' : String(meeting.reminder_minutes_before),
      notes: meeting.notes || '',
    });
    setPopover({ day, meeting });
  }

  function updateForm(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSave(e) {
    e.preventDefault();
    setError('');
    setSaving(true);
    try {
      const [hours, minutes] = form.time.split(':').map(Number);
      const start = new Date(popover.day);
      start.setHours(hours, minutes, 0, 0);
      const reminderMinutes = form.reminder === 'custom' ? Number(form.customReminder) : Number(form.reminder);
      const payload = {
        title: form.title,
        notes: form.notes,
        start_time: start.toISOString(),
        reminder_minutes_before: reminderMinutes,
      };
      if (popover.meeting) {
        await api.updateMeeting(popover.meeting.id, payload);
      } else {
        await api.createMeeting(payload);
      }
      setPopover(null);
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    setSaving(true);
    try {
      await api.deleteMeeting(popover.meeting.id);
      setPopover(null);
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="calendar-page">
      <header className="dashboard-header">
        <div className="dashboard-header-text">
          <h1>יומן</h1>
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
      </header>

      {error && !popover && <p className="error">{error}</p>}

      <div className="calendar-grid">
        {WEEKDAY_LABELS.map((label) => (
          <div key={label} className="calendar-weekday">{label}</div>
        ))}
        {days.map((day) => {
          const inMonth = day.getMonth() === viewMonth;
          const isToday = sameDay(day, today);
          const dayMeetings = meetingsForDay(day);
          return (
            <div
              key={day.toISOString()}
              className={`calendar-day${inMonth ? '' : ' outside'}${isToday ? ' today' : ''}`}
              onClick={() => dayMeetings.length === 0 && openCreate(day)}
            >
              <span className="calendar-day-number">{day.getDate()}</span>
              <div className="calendar-day-meetings">
                {dayMeetings.map((m) => (
                  <button
                    key={m.id}
                    type="button"
                    className="meeting-pill"
                    onClick={(e) => {
                      e.stopPropagation();
                      openMeeting(m, day);
                    }}
                  >
                    {new Date(m.start_time).toLocaleTimeString('he-IL', { hour: '2-digit', minute: '2-digit' })} {m.title}
                  </button>
                ))}
                {isSuperuser && dayMeetings.length > 0 && (
                  <button
                    type="button"
                    className="calendar-day-add"
                    onClick={(e) => {
                      e.stopPropagation();
                      openCreate(day);
                    }}
                    aria-label="הוספת פגישה נוספת"
                  >
                    + פגישה
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {meetings.length === 0 && !isSuperuser && (
        <p className="hint">אין פגישות מתוכננות החודש.</p>
      )}

      {popover && (
        <div className="calendar-popover-backdrop">
          <div className="calendar-popover" ref={popoverRef}>
            {isSuperuser ? (
              <form onSubmit={handleSave}>
                <div className="calendar-popover-header">
                  <h3>{popover.meeting ? 'עריכת פגישה' : 'פגישה חדשה'}</h3>
                  <button type="button" className="icon-nav-button" onClick={() => setPopover(null)} aria-label="סגירה">×</button>
                </div>
                <p className="hint">
                  {popover.day.toLocaleDateString('he-IL', { weekday: 'long', day: 'numeric', month: 'long' })}
                </p>
                <label>
                  כותרת
                  <input required value={form.title} onChange={(e) => updateForm('title', e.target.value)} />
                </label>
                <label>
                  שעה
                  <input required type="time" value={form.time} onChange={(e) => updateForm('time', e.target.value)} />
                </label>
                <label>
                  תזכורת לפני
                  <select value={form.reminder} onChange={(e) => updateForm('reminder', e.target.value)}>
                    <option value="5">5 דקות</option>
                    <option value="15">15 דקות</option>
                    <option value="30">30 דקות</option>
                    <option value="60">שעה</option>
                    <option value="1440">יום</option>
                    <option value="custom">מותאם אישית</option>
                  </select>
                </label>
                {form.reminder === 'custom' && (
                  <label>
                    מספר דקות לפני
                    <input
                      required
                      type="number"
                      min="1"
                      value={form.customReminder}
                      onChange={(e) => updateForm('customReminder', e.target.value)}
                    />
                  </label>
                )}
                <label>
                  הערות
                  <textarea value={form.notes} onChange={(e) => updateForm('notes', e.target.value)} />
                </label>

                {error && <p className="error">{error}</p>}

                <div className="form-actions">
                  <button type="submit" disabled={saving}>{saving ? 'שומר…' : 'שמירה'}</button>
                  {popover.meeting && (
                    <button type="button" className="danger" onClick={handleDelete} disabled={saving}>מחיקה</button>
                  )}
                  <button type="button" className="secondary" onClick={() => setPopover(null)}>ביטול</button>
                </div>
              </form>
            ) : (
              <div>
                <div className="calendar-popover-header">
                  <h3>{popover.meeting.title}</h3>
                  <button type="button" className="icon-nav-button" onClick={() => setPopover(null)} aria-label="סגירה">×</button>
                </div>
                <p className="mono">
                  {new Date(popover.meeting.start_time).toLocaleString('he-IL', { dateStyle: 'medium', timeStyle: 'short' })}
                </p>
                {popover.meeting.notes && <p>{popover.meeting.notes}</p>}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
