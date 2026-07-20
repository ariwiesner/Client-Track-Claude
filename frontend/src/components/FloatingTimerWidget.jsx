import { useEffect, useState } from 'react';
import { useTimer } from '../context/TimerContext';

function formatElapsed(ms) {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  return [h, m, s].map((n) => String(n).padStart(2, '0')).join(':');
}

export function FloatingTimerWidget() {
  const { entry, stoppedEntry, stop, cancel, resume, dismissStopped } = useTimer();
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    if (!entry) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [entry]);

  if (!entry && !stoppedEntry) return null;

  if (entry) {
    const elapsed = now - new Date(entry.start_time).getTime();
    return (
      <div className="floating-timer">
        <div className="floating-timer-info">
          <span className="floating-timer-client">{entry.client_name}</span>
          <span className="floating-timer-clock">{formatElapsed(elapsed)}</span>
        </div>
        <div className="floating-timer-actions">
          <button className="icon-button cancel" onClick={cancel} title="ביטול">
            ✕
          </button>
          <button className="stop-button" onClick={stop}>
            עצירה
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="floating-timer stopped">
      <div className="floating-timer-info">
        <span className="floating-timer-client">{stoppedEntry.client_name}</span>
        <span className="floating-timer-status">הופסק</span>
      </div>
      <div className="floating-timer-actions">
        <button className="icon-button cancel" onClick={dismissStopped} title="התעלמות">
          ✕
        </button>
        <button className="continue-button" onClick={resume}>
          המשך
        </button>
      </div>
    </div>
  );
}
