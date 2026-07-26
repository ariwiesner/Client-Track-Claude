import { Link } from 'react-router-dom';
import { SystemBreakdownChart } from './SystemBreakdownChart';

function ArrowIcon() {
  return (
    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.4" aria-hidden="true">
      <path d="M7 17 17 7M9 7h8v8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function KpiIconLink({ to, label }) {
  return (
    <Link to={to} className="kpi-icon-btn" title={label} aria-label={label}>
      <ArrowIcon />
    </Link>
  );
}

export function DashboardSummary({ summary, isStaff, clientCounts }) {
  if (!summary) {
    return (
      <section className="dashboard-summary">
        <p className="hint">טוען…</p>
      </section>
    );
  }

  const hasActivity =
    !!summary.top_client ||
    (isStaff && !!summary.top_worker) ||
    (summary.system_breakdown && summary.system_breakdown.length > 0);
  const isEmpty = clientCounts.all === 0 || !hasActivity;

  if (isEmpty) {
    return (
      <section className="dashboard-summary">
        <p className="hint">אין נתונים להצגה החודש.</p>
      </section>
    );
  }

  return (
    <section className="dashboard-summary">
      <h2 className="dashboard-summary-title">סיכום החודש</h2>

      <div className="kpi-row">
        <div className="kpi-card kpi-mint-group">
          <div className="kpi-mini-grid">
            <div className="kpi-mini">
              <span className="kpi-mini-label">סה״כ לקוחות</span>
              <span className="kpi-mini-value mono">{clientCounts.all}</span>
            </div>
            <div className="kpi-mini">
              <span className="kpi-mini-label">שולם החודש</span>
              <span className="kpi-mini-value mono">{clientCounts.paid}</span>
            </div>
            <div className="kpi-mini">
              <span className="kpi-mini-label">לא שולם</span>
              <span className="kpi-mini-value mono">{clientCounts.unpaid}</span>
            </div>
            <div className="kpi-mini">
              <span className="kpi-mini-label">עבדנו איתם החודש</span>
              <span className="kpi-mini-value mono">{clientCounts.worked}</span>
            </div>
          </div>
        </div>

        <div className="kpi-card kpi-yellow">
          <div className="kpi-card-head">
            <span className="kpi-label">הלקוח הפעיל ביותר</span>
            {summary.top_client && (
              <span className="kpi-badge">{summary.top_client.hours.toFixed(1)} ש׳</span>
            )}
          </div>
          {summary.top_client ? (
            <div className="kpi-card-foot">
              <span className="kpi-title">{summary.top_client.name}</span>
              <KpiIconLink
                to={`/clients/${summary.top_client.id}`}
                label={`מעבר ללקוח ${summary.top_client.name}`}
              />
            </div>
          ) : (
            <span className="kpi-title kpi-title-muted">אין נתונים</span>
          )}
        </div>

        {isStaff && (
          <div className="kpi-card kpi-purple">
            <div className="kpi-card-head">
              <span className="kpi-label">העובד הפעיל ביותר</span>
              {summary.top_worker && (
                <span className="kpi-badge">{summary.top_worker.hours.toFixed(1)} ש׳</span>
              )}
            </div>
            {summary.top_worker ? (
              <div className="kpi-card-foot">
                <span className="kpi-title">{summary.top_worker.name}</span>
                <KpiIconLink
                  to={`/workers/${summary.top_worker.id}`}
                  label={`מעבר לעובד ${summary.top_worker.name}`}
                />
              </div>
            ) : (
              <span className="kpi-title kpi-title-muted">אין נתונים</span>
            )}
          </div>
        )}
      </div>

      <div className="kpi-row">
        <div className="kpi-card kpi-accent">
          <div className="kpi-card-head">
            <span className="kpi-label">שעות עבודה החודש</span>
          </div>
          <span className="kpi-value mono">{summary.total_hours.toFixed(1)}</span>
        </div>

        {isStaff && summary.total_revenue !== null && (
          <div className="kpi-card kpi-ok">
            <div className="kpi-card-head">
              <span className="kpi-label">הכנסה החודש</span>
            </div>
            <span className="kpi-value mono">₪{summary.total_revenue.toFixed(0)}</span>
          </div>
        )}

        {isStaff && summary.total_unpaid !== null && (
          <div className="kpi-card kpi-warn">
            <div className="kpi-card-head">
              <span className="kpi-label">יתרת חוב פתוחה</span>
            </div>
            <span className="kpi-value mono">₪{summary.total_unpaid.toFixed(0)}</span>
          </div>
        )}
      </div>

      <div className="card system-breakdown-card">
        <h3 className="breakdown-title">שעות לפי מערכת</h3>
        <SystemBreakdownChart data={summary.system_breakdown} />
      </div>
    </section>
  );
}
