import { useEffect, useRef, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNotifications } from '../context/NotificationsContext';
import { enablePush, isPushSupported } from '../push';

function BellIcon() {
  return (
    <svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <path d="M12 3.5c-2.5 0-4.5 2-4.5 4.5v3.2c0 .6-.2 1.2-.6 1.7l-1.1 1.4c-.6.8 0 2 1 2h10.4c1 0 1.6-1.2 1-2l-1.1-1.4c-.4-.5-.6-1.1-.6-1.7V8c0-2.5-2-4.5-4.5-4.5Z" strokeLinejoin="round" />
      <path d="M10 19.5a2 2 0 0 0 4 0" strokeLinecap="round" />
    </svg>
  );
}

function formatWhen(iso) {
  return new Date(iso).toLocaleString('he-IL', { dateStyle: 'short', timeStyle: 'short' });
}

export function NotificationBell() {
  const { user } = useAuth();
  const { notifications, hasUnread, refresh, markRead } = useNotifications();
  const [open, setOpen] = useState(false);
  const [pushState, setPushState] = useState('idle'); // idle | working | done | error
  const rootRef = useRef(null);

  useEffect(() => {
    if (!isPushSupported()) return;
    navigator.serviceWorker.ready
      .then((reg) => reg.pushManager.getSubscription())
      .then((sub) => { if (sub) setPushState('done'); })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!open) return;
    function onClick(e) {
      if (rootRef.current && !rootRef.current.contains(e.target)) setOpen(false);
    }
    function onKey(e) {
      if (e.key === 'Escape') setOpen(false);
    }
    document.addEventListener('mousedown', onClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  if (!user?.is_superuser) return null;

  async function toggle() {
    const next = !open;
    setOpen(next);
    if (next) {
      await refresh();
      markRead();
    }
  }

  async function handleEnablePush() {
    setPushState('working');
    try {
      await enablePush();
      setPushState('done');
    } catch {
      setPushState('error');
    }
  }

  return (
    <div className="notification-bell-wrap" ref={rootRef}>
      <button
        className="icon-nav-button notification-bell-button"
        onClick={toggle}
        aria-label="התראות"
        title="התראות"
      >
        <BellIcon />
        {hasUnread && <span className="notification-dot" aria-hidden="true" />}
      </button>
      {open && (
        <div className="notification-panel">
          <div className="notification-panel-header">התראות</div>
          {isPushSupported() && (
            <button
              className="notification-push-button"
              onClick={handleEnablePush}
              disabled={pushState === 'working' || pushState === 'done'}
            >
              {pushState === 'done' && 'התראות הופעלו ✓'}
              {pushState === 'working' && 'מפעיל...'}
              {pushState === 'error' && 'ההפעלה נכשלה — נסה שוב'}
              {pushState === 'idle' && 'הפעל התראות במכשיר זה'}
            </button>
          )}
          {notifications.length === 0 ? (
            <p className="notification-empty">אין התראות</p>
          ) : (
            <ul className="notification-list">
              {notifications.map((n) => (
                <li key={n.id} className={`notification-item${n.is_read ? '' : ' unread'}`}>
                  <span className="notification-message">{n.message}</span>
                  <span className="notification-time">{formatWhen(n.created_at)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
