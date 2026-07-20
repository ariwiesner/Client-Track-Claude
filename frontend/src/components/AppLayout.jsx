import { useEffect, useMemo, useState } from 'react';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { Sidebar } from './Sidebar';

const STATIC_TITLES = {
  '/': 'לוח בקרה',
  '/clients/new': 'הוספת לקוח',
  '/systems': 'מערכות',
  '/systems/new': 'הוספת מערכת',
  '/manual-entry': 'רישום שעות',
  '/workers': 'עובדים',
  '/profile': 'הפרופיל שלי',
  '/receipts': 'קבלות',
};

function pageTitle(pathname) {
  if (pathname in STATIC_TITLES) return STATIC_TITLES[pathname];
  if (/^\/clients\/\d+\/edit$/.test(pathname)) return 'עריכת לקוח';
  if (/^\/clients\/\d+$/.test(pathname)) return 'פרטי לקוח';
  if (/^\/systems\/\d+\/edit$/.test(pathname)) return 'עריכת מערכת';
  if (/^\/workers\/\d+$/.test(pathname)) return 'פרטי עובד';
  return null;
}

function userInitial(user) {
  const source = user?.first_name || user?.username || '?';
  return source.charAt(0).toUpperCase();
}

function greeting() {
  const hour = new Date().getHours();
  if (hour >= 4 && hour < 12) return 'בוקר טוב';
  if (hour >= 12 && hour < 17) return 'צהריים טובים';
  if (hour >= 17 && hour < 21) return 'ערב טוב';
  return 'לילה טוב';
}

export function AppLayout() {
  const { user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const isHome = location.pathname === '/';
  const title = pageTitle(location.pathname);
  const avatarColor = useMemo(() => Math.floor(Math.random() * 6) + 1, []);
  const [isFirstPlace, setIsFirstPlace] = useState(false);

  useEffect(() => {
    const now = new Date();
    api
      .getMySummary(now.getFullYear(), now.getMonth() + 1)
      .then((summary) => setIsFirstPlace(summary.is_first_place))
      .catch(() => {});
  }, []);

  return (
    <div className="app-shell">
      <Sidebar />
      <div className="app-content">
        <header className="app-header">
          <div className="app-header-left">
            {!isHome && (
              <button
                className="icon-nav-button back-icon"
                onClick={() => navigate(-1)}
                aria-label="חזרה"
                title="חזרה"
              >
                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M15 18l-6-6 6-6" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            )}
            {title && <span className="page-title">{title}</span>}
          </div>
          <div className="app-header-right">
            <span className="user-identity">
              <span className="user-name">
                {greeting()}, {user?.first_name || user?.username}!
              </span>
              <Link to="/profile" className="user-avatar-wrap" title="הפרופיל שלי">
                {isFirstPlace && <span className="user-avatar-crown" aria-hidden="true">👑</span>}
                <span className={`user-avatar avatar-color-${avatarColor}`} aria-hidden="true">
                  {userInitial(user)}
                </span>
              </Link>
            </span>
          </div>
        </header>
        <main className="app-main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
