import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

function GridIcon() {
  return (
    <svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <rect x="3.5" y="3.5" width="7" height="7" rx="1.6" />
      <rect x="13.5" y="3.5" width="7" height="7" rx="1.6" />
      <rect x="3.5" y="13.5" width="7" height="7" rx="1.6" />
      <rect x="13.5" y="13.5" width="7" height="7" rx="1.6" />
    </svg>
  );
}
function UserPlusIcon() {
  return (
    <svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <circle cx="9" cy="8" r="3.5" />
      <path d="M2.5 20c1.2-3.6 3.7-5.5 6.5-5.5s5.3 1.9 6.5 5.5" strokeLinecap="round" />
      <path d="M18.5 8v6M15.5 11h6" strokeLinecap="round" />
    </svg>
  );
}
function LayersIcon() {
  return (
    <svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <path d="M12 3.5 21 8l-9 4.5L3 8l9-4.5Z" strokeLinejoin="round" />
      <path d="m3 12.5 9 4.5 9-4.5M3 16.5l9 4.5 9-4.5" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}
function ClockIcon() {
  return (
    <svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V12l3 2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
function UsersIcon() {
  return (
    <svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <circle cx="8.5" cy="8" r="3.2" />
      <path d="M2.5 20c1.1-3.4 3.4-5.2 6-5.2s4.9 1.8 6 5.2" strokeLinecap="round" />
      <circle cx="17" cy="8.5" r="2.6" />
      <path d="M15.8 15.2c2.2.4 3.7 2 4.5 4.5" strokeLinecap="round" />
    </svg>
  );
}
function ReceiptIcon() {
  return (
    <svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <path d="M6 3.5h12v16l-2-1.3-2 1.3-2-1.3-2 1.3-2-1.3-2 1.3v-16Z" strokeLinejoin="round" />
      <path d="M8.5 8h7M8.5 11.5h7M8.5 15h4" strokeLinecap="round" />
    </svg>
  );
}
function LogoutIcon() {
  return (
    <svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <path d="M9 4.5H6a1.5 1.5 0 0 0-1.5 1.5v12A1.5 1.5 0 0 0 6 19.5h3" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M15.5 16 20 12l-4.5-4M20 12H9.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

const NAV_ITEMS = [
  { to: '/', label: 'לוח בקרה', Icon: GridIcon, end: true },
  { to: '/clients/new', label: 'הוספת לקוח', Icon: UserPlusIcon },
  { to: '/systems', label: 'מערכות', Icon: LayersIcon },
  { to: '/manual-entry', label: 'רישום שעות', Icon: ClockIcon },
  { to: '/receipts', label: 'קבלות', Icon: ReceiptIcon },
];

export function Sidebar() {
  const { user, logout } = useAuth();
  const navItems = user?.is_staff
    ? [...NAV_ITEMS, { to: '/workers', label: 'עובדים', Icon: UsersIcon }]
    : NAV_ITEMS;

  return (
    <aside className="sidebar">
      <NavLink to="/" className="sidebar-brand" aria-label="בית">
        <span className="brand-mark">CT</span>
        <span className="sidebar-brand-name">מעקב לקוחות</span>
      </NavLink>

      <nav className="sidebar-nav">
        {navItems.map(({ to, label, Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}
          >
            <Icon />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      <button className="sidebar-logout" onClick={logout}>
        <LogoutIcon />
        <span>התנתקות</span>
      </button>
    </aside>
  );
}
