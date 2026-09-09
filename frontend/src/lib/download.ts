import { api } from "./api";

// نقاط التصدير محمية بتوكن — رابط <a href> مباشر ما يقدر يحمل Authorization header،
// فلازم نجيب الملف عبر axios (يضيف التوكن تلقائياً) ونولّد blob URL للتنزيل الفعلي.
export async function downloadInvoiceExport(invoiceId: number | string, filename: string) {
  const res = await api.get(`/invoices/${invoiceId}/export/download`, { responseType: "blob" });
  const url = URL.createObjectURL(res.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
