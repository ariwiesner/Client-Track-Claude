import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.jsx'
import { AuthProvider } from './context/AuthContext.jsx'
import { TimerProvider } from './context/TimerContext.jsx'
import { NotificationsProvider } from './context/NotificationsContext.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <TimerProvider>
          <NotificationsProvider>
            <App />
          </NotificationsProvider>
        </TimerProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
