import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useAuth } from './AuthContext';

const NotificationsContext = createContext(null);

const POLL_MS = 15000;

export function NotificationsProvider({ children }) {
  const { user } = useAuth();
  const enabled = !!user?.is_superuser;
  const [notifications, setNotifications] = useState([]);

  const refresh = useCallback(async () => {
    if (!enabled) return;
    setNotifications(await api.listNotifications());
  }, [enabled]);

  useEffect(() => {
    if (!enabled) {
      setNotifications([]);
      return;
    }
    refresh();
    const id = setInterval(refresh, POLL_MS);
    window.addEventListener('focus', refresh);
    return () => {
      clearInterval(id);
      window.removeEventListener('focus', refresh);
    };
  }, [enabled, refresh]);

  const hasUnread = notifications.some((n) => !n.is_read);

  const markRead = useCallback(async () => {
    if (!hasUnread) return;
    setNotifications((list) => list.map((n) => ({ ...n, is_read: true })));
    await api.markNotificationsRead();
  }, [hasUnread]);

  return (
    <NotificationsContext.Provider value={{ notifications, hasUnread, refresh, markRead }}>
      {children}
    </NotificationsContext.Provider>
  );
}

export function useNotifications() {
  return useContext(NotificationsContext);
}
