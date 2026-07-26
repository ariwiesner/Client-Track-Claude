const COLOR_SLOTS = 6;
const MAX_ROWS = 6;
const OTHER_LABEL = 'אחר';

// Assigns each system a stable color slot based on its name's position in an
// alphabetically-sorted list of distinct names — NOT its hours rank — so a
// system's color never changes just because the ranking shifted between
// months.
function buildColorIndex(data) {
  const names = Array.from(new Set(data.map((row) => row.system_name))).sort((a, b) =>
    a.localeCompare(b, 'he')
  );
  return new Map(names.map((name, index) => [name, index % COLOR_SLOTS]));
}

export function SystemBreakdownChart({ data }) {
  if (!data || data.length === 0) {
    return <p className="hint">לא נרשמו שעות החודש.</p>;
  }

  const colorIndex = buildColorIndex(data);

  let rows = data;
  if (data.length > MAX_ROWS) {
    const sortedByHours = [...data].sort((a, b) => b.hours - a.hours);
    const kept = sortedByHours.slice(0, MAX_ROWS - 1);
    const rest = sortedByHours.slice(MAX_ROWS - 1);
    const otherHours = rest.reduce((sum, row) => sum + row.hours, 0);
    rows = [...kept, { system_name: OTHER_LABEL, hours: otherHours, isOther: true }];
  }

  const displayRows = [...rows].sort((a, b) => b.hours - a.hours);
  const maxHours = Math.max(...displayRows.map((row) => row.hours), 0);

  return (
    <div className="system-breakdown-chart">
      {displayRows.map((row) => {
        const colorSlot = row.isOther ? null : colorIndex.get(row.system_name);
        const width = maxHours > 0 ? (row.hours / maxHours) * 100 : 0;
        const bg = row.isOther ? 'var(--grey-100)' : `var(--avatar-${colorSlot + 1}-bg)`;
        const fg = row.isOther ? 'var(--text-muted)' : `var(--avatar-${colorSlot + 1}-fg)`;
        return (
          <div className="system-breakdown-row" style={{ background: bg, color: fg }} key={row.system_name}>
            <span className="system-breakdown-label">{row.system_name}</span>
            <div className="system-breakdown-track">
              <div className="system-breakdown-bar" style={{ width: `${width}%`, background: fg }} />
            </div>
            <span className="system-breakdown-value">{row.hours.toFixed(1)} שעות</span>
          </div>
        );
      })}
    </div>
  );
}
