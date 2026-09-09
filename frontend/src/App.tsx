import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./lib/auth";
import Login from "./pages/Login";
import Stores from "./pages/Stores";
import Invoices from "./pages/Invoices";
import InvoiceReview from "./pages/InvoiceReview";
import InvoiceSession from "./pages/InvoiceSession";
import InvoiceReconciliation from "./pages/InvoiceReconciliation";
import ComingSoon from "./components/ComingSoon";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function Routed() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      <Route path="/stores" element={<ProtectedRoute><Stores /></ProtectedRoute>} />
      <Route
        path="/stores/:storeId/invoices"
        element={<ProtectedRoute><Invoices /></ProtectedRoute>}
      />
      <Route
        path="/stores/:storeId/inventory"
        element={<ProtectedRoute><ComingSoon title="المخزون" /></ProtectedRoute>}
      />
      <Route
        path="/stores/:storeId/history"
        element={<ProtectedRoute><ComingSoon title="سجل الفواتير" /></ProtectedRoute>}
      />

      <Route
        path="/invoices/:invoiceId/review"
        element={<ProtectedRoute><InvoiceReview /></ProtectedRoute>}
      />
      <Route
        path="/invoices/:invoiceId/session"
        element={<ProtectedRoute><InvoiceSession /></ProtectedRoute>}
      />
      <Route
        path="/invoices/:invoiceId/reconciliation"
        element={<ProtectedRoute><InvoiceReconciliation /></ProtectedRoute>}
      />
      <Route
        path="/invoices/:invoiceId/export"
        element={<ProtectedRoute><ComingSoon title="التصدير النهائي" /></ProtectedRoute>}
      />

      <Route path="/" element={<Navigate to="/stores" replace />} />
      <Route path="*" element={<Navigate to="/stores" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <Routed />
    </AuthProvider>
  );
}
