import { useNavigate } from 'react-router-dom';

const MAX_WORKER_AVATARS = 4;
const AVATAR_COLOR_COUNT = 6;

function whatsAppLink(phone) {
  if (!phone) return null;
  let digits = phone.replace(/\D/g, '');
  if (!digits) return null;
  if (digits.startsWith('0')) {
    digits = '972' + digits.slice(1); // מספר ישראלי מקומי -> בינלאומי
  }
  return `https://wa.me/${digits}`;
}

function AnonymousAvatarIcon() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <circle cx="12" cy="8" r="3.5" />
      <path d="M4.5 20c1.4-3.6 4.4-5.5 7.5-5.5s6.1 1.9 7.5 5.5" strokeLinecap="round" />
    </svg>
  );
}

function WhatsAppIcon() {
  return (
    <svg viewBox="0 0 24 24" width="26" height="26" fill="#25D366" aria-hidden="true">
      <path d="M12.001 2.003c-5.514 0-9.997 4.483-9.997 9.997 0 1.762.464 3.484 1.346 4.997L2 22l5.129-1.345a9.96 9.96 0 0 0 4.872 1.242h.005c5.514 0 9.997-4.483 9.997-9.997 0-2.67-1.04-5.18-2.929-7.069a9.935 9.935 0 0 0-7.073-2.925zm.004 18.11h-.004a8.17 8.17 0 0 1-4.164-1.14l-.299-.177-3.098.812.827-3.023-.194-.31a8.16 8.16 0 0 1-1.257-4.35c0-4.516 3.674-8.19 8.19-8.19a8.14 8.14 0 0 1 5.795 2.398 8.14 8.14 0 0 1 2.395 5.796c0 4.516-3.674 8.184-8.191 8.184z" />
      <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z" />
    </svg>
  );
}

export function ClientCard({ billing, workers = [], index = 0, isRunningHere, onStart, onTogglePaid, startDisabled }) {
  const { client } = billing;
  const navigate = useNavigate();
  const colorIndex = (index % AVATAR_COLOR_COUNT) + 1;

  function goToDetail() {
    navigate(`/clients/${client.id}`);
  }

  function stopPropagation(e, fn) {
    e.stopPropagation();
    fn();
  }

  const visibleWorkers = workers.slice(0, MAX_WORKER_AVATARS);
  const extraWorkers = workers.length - visibleWorkers.length;
  const owesMoney = Number(billing.amount_owed) > 0;
  const waLink = whatsAppLink(client.phone);

  return (
    <div
      className={`client-card ${owesMoney ? (billing.paid ? 'paid' : 'unpaid') : ''}`}
      onClick={goToDetail}
      onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && goToDetail()}
      role="button"
      tabIndex={0}
    >
      {owesMoney && (
        <span className={`status-pill ${billing.paid ? 'paid' : 'unpaid'}`}>
          {billing.paid ? 'שולם' : 'לא שולם'}
        </span>
      )}

      <div className="client-card-header">
        <span className={`avatar-circle avatar-color-${colorIndex}`} aria-hidden="true">
          <AnonymousAvatarIcon />
        </span>
        <div className="client-card-identity">
          <h3>{client.name}</h3>
          {client.tax_subject && <p className="job-type">{client.tax_subject}</p>}
          {client.job_type && <p className="job-type">{client.job_type}</p>}
        </div>
      </div>

      <div className="client-card-stats">
        <div className="client-card-stat">
          <span className="client-card-stat-label">שעות החודש</span>
          <span className="client-card-stat-value mono">{Number(billing.total_hours).toFixed(2)}</span>
        </div>
        <div className="client-card-stat">
          <span className="client-card-stat-label">לתשלום</span>
          <span className="client-card-stat-value mono">₪{Number(billing.amount_owed).toFixed(2)}</span>
        </div>
      </div>

      <div className="client-card-footer">
        <div className="avatar-stack" title={workers.map((w) => w.label).join(', ')}>
          {visibleWorkers.length === 0 && <span className="avatar-stack-empty">אין רישומים החודש</span>}
          {visibleWorkers.map((worker) => (
            <span key={worker.id} className="avatar avatar-worker" title={worker.label}>
              {worker.label.charAt(0).toUpperCase()}
            </span>
          ))}
          {extraWorkers > 0 && <span className="avatar avatar-overflow">+{extraWorkers}</span>}
        </div>

        <div className="client-card-actions">
          {waLink && (
            <a
              href={waLink}
              target="_blank"
              rel="noopener noreferrer"
              className="card-whatsapp-icon"
              title="פתיחת שיחת וואטסאפ"
              aria-label={`שליחת הודעה ל${client.name} בוואטסאפ`}
              onClick={(e) => e.stopPropagation()}
            >
              <WhatsAppIcon />
            </a>
          )}
          <button
            onClick={(e) => stopPropagation(e, () => onStart(client.id))}
            disabled={startDisabled}
            className={`${isRunningHere ? 'active' : ''} ${owesMoney ? '' : 'full-width'}`}
          >
            {isRunningHere ? 'הטיימר פעיל…' : 'הפעלת טיימר'}
          </button>
          {owesMoney && (
            <button
              className="paid-toggle"
              onClick={(e) => stopPropagation(e, () => onTogglePaid(billing.id))}
            >
              סמן כ{billing.paid ? 'לא שולם' : 'שולם'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
