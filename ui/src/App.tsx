import { BrowserRouter, Route, Routes } from "react-router-dom";
import { ToastProvider } from "./components/Toast/ToastContext";
import { InvoiceDetailPage } from "./pages/InvoiceDetailPage";
import { ReviewQueuePage } from "./pages/ReviewQueuePage";

export function App() {
  return (
    <ToastProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<ReviewQueuePage />} />
          <Route path="/invoices/:invoiceId" element={<InvoiceDetailPage />} />
        </Routes>
      </BrowserRouter>
    </ToastProvider>
  );
}
