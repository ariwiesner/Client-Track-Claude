import { api } from './api/client'

// This feature-detect is the entire Apple/Safari exclusion — push just
// isn't supported there, no further special-casing needed.
export function isPushSupported() {
  return 'serviceWorker' in navigator && 'PushManager' in window
}

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = atob(base64)
  return Uint8Array.from([...rawData].map((c) => c.charCodeAt(0)))
}

export async function enablePush() {
  const permission = await Notification.requestPermission()
  if (permission !== 'granted') {
    throw new Error('הרשאת התראות נדחתה')
  }
  const registration = await navigator.serviceWorker.ready
  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(import.meta.env.VITE_VAPID_PUBLIC_KEY),
  })
  await api.subscribePush(subscription.toJSON())
}
