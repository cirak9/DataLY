import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./lib/auth";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Stores from "./pages/Stores";
import Invoices from "./pages/Invoices";
import InvoiceReview from "./pages/InvoiceReview";
import InvoiceSession from "./pages/InvoiceSession";
import InvoiceReconciliation from "./pages/InvoiceReconciliation";
import InvoiceExport from "./pages/InvoiceExport";
import Inventory from "./pages/Inventory";
import InvoiceHistory from "./pages/InvoiceHistory";
import OcrUpload from "./pages/OcrUpload";
import OcrReview from "./pages/OcrReview";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function Routed() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      <Route path="/stores" element={<ProtectedRoute><Stores /></ProtectedRoute>} />
      <Route
        path="/stores/:storeId/invoices"
        element={<ProtectedRoute><Invoices /></ProtectedRoute>}
      />
      <Route
        path="/stores/:storeId/inventory"
        element={<ProtectedRoute><Inventory /></ProtectedRoute>}
      />
      <Route
        path="/stores/:storeId/history"
        element={<ProtectedRoute><InvoiceHistory /></ProtectedRoute>}
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
        element={<ProtectedRoute><InvoiceExport /></ProtectedRoute>}
      />
      <Route
        path="/stores/:storeId/invoices/ocr-upload"
        element={<ProtectedRoute><OcrUpload /></ProtectedRoute>}
      />
      <Route
        path="/invoices/:invoiceId/ocr-review"
        element={<ProtectedRoute><OcrReview /></ProtectedRoute>}
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
