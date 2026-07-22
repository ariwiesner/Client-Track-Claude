import { SystemBreakdownChart } from './SystemBreakdownChart';

export function DashboardSummary({ summary, isStaff }) {
  if (!summary) {
    return (
      <section className="card dashboard-summary">
        <p className="hint">טוען…</p>
      </section>
    );
  }

  const hasActivity =
    !!summary.top_client ||
    (isStaff && !!summary.top_worker) ||
    (summary.system_breakdown && summary.system_breakdown.length > 0);
  const isEmpty = summary.total_clients === 0 || !hasActivity;

  if (isEmpty) {
    return (
      <section className="card dashboard-summary">
        <p className="hint">אין נתונים להצגה החודש.</p>
      </section>
    );
  }

  return (
    <section className="card dashboard-summary">
      <div className="stat-bar">
        <div className="stat-bar-stats">
          <div className="stat-tile">
            <span className="stat-label">לקוחות פעילים</span>
            <span className="stat-value mono">{summary.total_clients}</span>
          </div>
          <div className="stat-tile">
            <span className="stat-label">הלקוח הפעיל ביותר החודש</span>
            <span className="stat-value mono">
              {summary.top_client
                ? `${summary.top_client.name} · ${summary.top_client.hours.toFixed(2)} שעות`
                : '—'}
            </span>
          </div>
          {isStaff && summary.top_worker && (
            <div className="stat-tile">
              <span className="stat-label">העובד הפעיל ביותר החודש</span>
              <span className="stat-value mono">
                {summary.top_worker.name} · {summary.top_worker.hours.toFixed(2)} שעות
              </span>
            </div>
          )}
        </div>
      </div>

      <SystemBreakdownChart data={summary.system_breakdown} />
    </section>
  );
}
