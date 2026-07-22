import { useEffect, useState, useCallback, useMemo } from 'react';
import { Link } from 'react-router-dom';
import * as XLSX from 'xlsx';
import { api } from '../api/client';
import { ClientCard } from '../components/ClientCard';
import { DashboardSummary } from '../components/DashboardSummary';
import { useAuth } from '../context/AuthContext';
import { useTimer } from '../context/TimerContext';
import { groupHoursBySystem, distinctWorkersForMonth } from '../utils/breakdown';

function ExcelIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" aria-hidden="true">
      <rect x="2" y="3" width="20" height="18" rx="2" fill="#207245" />
      <path
        d="M7.2 8.2 10 12l-2.8 3.8h1.9L11 13l1.9 2.8h1.9L12 12l2.8-3.8h-1.9L11 11l-1.9-2.8H7.2Z"
        fill="#fff"
      />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <circle cx="10.5" cy="10.5" r="6.5" />
      <path d="m20 20-4.5-4.5" strokeLinecap="round" />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2.2" aria-hidden="true">
      <path d="M12 5v14M5 12h14" strokeLinecap="round" />
    </svg>
  );
}

function ChevronIcon({ direction }) {
  const d = direction === 'next' ? 'M9 6l6 6-6 6' : 'M15 6l-6 6 6 6';
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d={d} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

const FILTERS = [
  { key: 'all', label: 'הכל' },
  { key: 'paid', label: 'שולם' },
  { key: 'unpaid', label: 'לא שולם' },
];

export function DashboardPage() {
  const [billings, setBillings] = useState([]);
  const [workersByClient, setWorkersByClient] = useState({});
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState('');
  const [exporting, setExporting] = useState(false);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');
  const { entry, start } = useTimer();
  const { user } = useAuth();

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
      const [data] = await Promise.all([
        api.listBilling(viewYear, viewMonth + 1),
        api.getDashboardSummary(viewYear, viewMonth + 1).then(setSummary),
      ]);
      setBillings(data);

      const billingsWithHours = data.filter(
        (billing) => Number(billing.total_hours) > 0 || billing.client.id === entry?.client
      );
      const workerEntries = await Promise.all(
        billingsWithHours.map(async (billing) => {
          const entries = await api.listTimeEntriesForClient(billing.client.id);
          const workers = distinctWorkersForMonth(entries, viewYear, viewMonth);
          return [billing.client.id, workers];
        })
      );
      setWorkersByClient(Object.fromEntries(workerEntries));
    } catch (err) {
      setError(err.message);
    }
  }, [entry?.client, viewYear, viewMonth]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleStart(clientId) {
    try {
      await start(clientId, { source: 'manual' });
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleTogglePaid(billingId) {
    await api.togglePaid(billingId);
    load();
  }

  async function handleExport() {
    setError('');
    setExporting(true);
    try {
      const clients = await api.listClients();
      const rows = [];
      for (const client of clients) {
        const entries = await api.listTimeEntriesForClient(client.id);
        const breakdown = groupHoursBySystem(entries, viewYear, viewMonth);
        if (breakdown.length === 0) {
          rows.push({ לקוח: client.name, מערכת: '—', 'שעות החודש': 0 });
        } else {
          for (const [system, hours] of breakdown) {
            rows.push({ לקוח: client.name, מערכת: system, 'שעות החודש': Number(hours.toFixed(2)) });
          }
        }
      }

      const sheet = XLSX.utils.json_to_sheet(rows);
      sheet['!cols'] = [{ wch: 24 }, { wch: 20 }, { wch: 14 }];
      const workbook = XLSX.utils.book_new();
      const exportMonthLabel = new Date(viewYear, viewMonth, 1).toLocaleString('he-IL', { month: 'long' });
      XLSX.utils.book_append_sheet(workbook, sheet, `${exportMonthLabel} ${viewYear}`);
      XLSX.writeFile(workbook, `שעות-לקוחות-${exportMonthLabel}-${viewYear}.xlsx`);
    } catch (err) {
      setError(err.message);
    } finally {
      setExporting(false);
    }
  }

  const counts = useMemo(
    () => ({
      all: billings.length,
      paid: billings.filter((b) => b.paid).length,
      unpaid: billings.filter((b) => !b.paid).length,
    }),
    [billings]
  );

  const visibleBillings = useMemo(() => {
    const query = search.trim().toLowerCase();
    return billings
      .filter((billing) => {
        if (filter === 'paid' && !billing.paid) return false;
        if (filter === 'unpaid' && billing.paid) return false;
        if (!query) return true;
        const { client } = billing;
        return (
          client.name.toLowerCase().includes(query) ||
          (client.job_type || '').toLowerCase().includes(query) ||
          (client.phone || '').toLowerCase().includes(query)
        );
      })
      .sort((a, b) => {
        const aOwes = Number(a.amount_owed) > 0 ? 1 : 0;
        const bOwes = Number(b.amount_owed) > 0 ? 1 : 0;
        return bOwes - aOwes;
      });
  }, [billings, filter, search]);

  return (
    <div className="dashboard-page">
      <header className="dashboard-header">
        <div className="dashboard-header-text">
          <h1>לקוחות</h1>
          <div className="month-nav">
            <button
              className="icon-nav-button"
              onClick={goToPrevMonth}
              title="החודש הקודם"
              aria-label="החודש הקודם"
            >
              <ChevronIcon direction="prev" />
            </button>
            <span className="month-nav-label">{monthLabel}</span>
            <button
              className="icon-nav-button"
              onClick={goToNextMonth}
              title="החודש הבא"
              aria-label="החודש הבא"
            >
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
        <div className="header-actions">
          <Link to="/clients/new" className="add-fab" title="הוספת לקוח" aria-label="הוספת לקוח">
            <PlusIcon />
          </Link>
          <Link to="/systems" className="button secondary">מערכות</Link>
          <Link to="/manual-entry" className="button secondary">רישום שעות</Link>
          <button
            className="icon-nav-button"
            onClick={handleExport}
            disabled={exporting}
            title="ייצוא לאקסל"
            aria-label="ייצוא לאקסל"
          >
            <ExcelIcon />
          </button>
        </div>
      </header>

      <DashboardSummary summary={summary} isStaff={!!user?.is_staff} />

      <div className="dashboard-toolbar">
        <div className="filter-tabs">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              className={`filter-tab${filter === f.key ? ' active' : ''}`}
              onClick={() => setFilter(f.key)}
            >
              {f.label}
              <span className="filter-tab-count">{counts[f.key]}</span>
            </button>
          ))}
        </div>
        <label className="search-box">
          <SearchIcon />
          <input
            type="text"
            placeholder="חיפוש לקוח, טלפון או תפקיד…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
      </div>

      {error && <p className="error">{error}</p>}

      <div className="client-grid">
        {visibleBillings.map((billing, index) => (
          <ClientCard
            key={billing.id}
            billing={billing}
            index={index}
            workers={workersByClient[billing.client.id] || []}
            isRunningHere={entry?.client === billing.client.id}
            startDisabled={!!entry || !isCurrentMonth}
            onStart={handleStart}
            onTogglePaid={handleTogglePaid}
          />
        ))}
      </div>

      {billings.length === 0 && <p className="hint">עדיין אין לקוחות — הוסיפו לקוח כדי להתחיל.</p>}
      {billings.length > 0 && visibleBillings.length === 0 && (
        <p className="hint">לא נמצאו לקוחות התואמים את החיפוש.</p>
      )}
    </div>
  );
}
