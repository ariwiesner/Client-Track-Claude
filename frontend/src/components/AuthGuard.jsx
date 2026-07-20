import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export function AuthGuard({ children }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return children;
}
