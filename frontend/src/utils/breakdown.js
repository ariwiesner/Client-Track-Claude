export function groupHoursBySystem(entries, year, month) {
  const totals = new Map();
  for (const entry of entries) {
    if (entry.status !== 'stopped') continue;
    const start = new Date(entry.start_time);
    if (start.getFullYear() !== year || start.getMonth() !== month) continue;
    const label = entry.system_name || 'Manual';
    totals.set(label, (totals.get(label) || 0) + Number(entry.duration_hours));
  }
  return [...totals.entries()].sort((a, b) => b[1] - a[1]);
}

export function distinctWorkersForMonth(entries, year, month) {
  const workers = new Map();
  for (const entry of entries) {
    if (entry.status === 'cancelled') continue;
    const start = new Date(entry.start_time);
    if (start.getFullYear() !== year || start.getMonth() !== month) continue;
    const { employee } = entry;
    if (!employee || workers.has(employee.id)) continue;
    workers.set(employee.id, {
      id: employee.id,
      label: employee.first_name || employee.username,
    });
  }
  return [...workers.values()];
}
