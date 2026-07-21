import { Routes, Route } from 'react-router-dom';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { ClientFormPage } from './pages/ClientFormPage';
import { ClientDetailPage } from './pages/ClientDetailPage';
import { SystemFormPage } from './pages/SystemFormPage';
import { SystemsPage } from './pages/SystemsPage';
import { ManualTimeEntryPage } from './pages/ManualTimeEntryPage';
import { WorkersPage } from './pages/WorkersPage';
import { WorkerDetailPage } from './pages/WorkerDetailPage';
import { ProfilePage } from './pages/ProfilePage';
import { ReceiptChatPage } from './pages/ReceiptChatPage';
import { CalendarPage } from './pages/CalendarPage';
import { AuthGuard } from './components/AuthGuard';
import { AppLayout } from './components/AppLayout';
import { FloatingTimerWidget } from './components/FloatingTimerWidget';
import { useAuth } from './context/AuthContext';

function App() {
  const { user } = useAuth();

  return (
    <>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          element={
            <AuthGuard>
              <AppLayout />
            </AuthGuard>
          }
        >
          <Route path="/" element={<DashboardPage />} />
          <Route path="/clients/new" element={<ClientFormPage />} />
          <Route path="/clients/:id" element={<ClientDetailPage />} />
          <Route path="/clients/:id/edit" element={<ClientFormPage />} />
          <Route path="/systems" element={<SystemsPage />} />
          <Route path="/systems/new" element={<SystemFormPage />} />
          <Route path="/systems/:id/edit" element={<SystemFormPage />} />
          <Route path="/manual-entry" element={<ManualTimeEntryPage />} />
          <Route path="/workers" element={<WorkersPage />} />
          <Route path="/workers/:id" element={<WorkerDetailPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/receipts" element={<ReceiptChatPage />} />
          <Route path="/calendar" element={<CalendarPage />} />
        </Route>
      </Routes>

      {user && <FloatingTimerWidget />}
    </>
  );
}

export default App;
