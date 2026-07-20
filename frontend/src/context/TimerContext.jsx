import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { useAuth } from './AuthContext';

const TimerContext = createContext(null);

const POLL_MS = 5000;

export function TimerProvider({ children }) {
  const { user } = useAuth();
  const [entry, setEntry] = useState(null); // running entry, from server truth
  const [stoppedEntry, setStoppedEntry] = useState(null); // local-only "awaiting continue"
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!user) return;
    const current = await api.currentTimeEntry();
    setEntry(current);
    if (current) setStoppedEntry(null);
    setLoading(false);
  }, [user]);

  useEffect(() => {
    if (!user) {
      setEntry(null);
      setStoppedEntry(null);
      return;
    }
    refresh();
    const id = setInterval(refresh, POLL_MS);
    window.addEventListener('focus', refresh);
    return () => {
      clearInterval(id);
      window.removeEventListener('focus', refresh);
    };
  }, [user, refresh]);

  const start = useCallback(async (clientId, opts = {}) => {
    const newEntry = await api.startTimeEntry({
      client_id: clientId,
      source: opts.source || 'manual',
      system_id: opts.systemId,
    });
    setEntry(newEntry);
    setStoppedEntry(null);
    return newEntry;
  }, []);

  const stop = useCallback(async () => {
    if (!entry) return;
    const stopped = await api.stopTimeEntry(entry.id);
    setEntry(null);
    setStoppedEntry(stopped);
  }, [entry]);

  const cancel = useCallback(async () => {
    if (!entry) return;
    await api.cancelTimeEntry(entry.id);
    setEntry(null);
    setStoppedEntry(null);
  }, [entry]);

  const resume = useCallback(async () => {
    if (!stoppedEntry) return;
    const newEntry = await api.resumeTimeEntry(stoppedEntry.id);
    setEntry(newEntry);
    setStoppedEntry(null);
    return newEntry;
  }, [stoppedEntry]);

  const dismissStopped = useCallback(() => setStoppedEntry(null), []);

  return (
    <TimerContext.Provider
      value={{ entry, stoppedEntry, loading, refresh, start, stop, cancel, resume, dismissStopped }}
    >
      {children}
    </TimerContext.Provider>
  );
}

export function useTimer() {
  return useContext(TimerContext);
}
