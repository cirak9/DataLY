import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { Invoice, Store } from "../lib/types";
import Layout from "../components/Layout";
import StatusBadge from "../components/StatusBadge";

function nextStepPath(invoice: Invoice): string {
  switch (invoice.status) {
    case "uploaded":
    case "cleaned":
      return `/invoices/${invoice.id}/review`;
    case "session_pending":
      return `/invoices/${invoice.id}/session`;
    case "session_complete":
    case "reconciled":
      return `/invoices/${invoice.id}/reconciliation`;
    default:
      return `/invoices/${invoice.id}/export`;
  }
}

export default function Invoices() {
  const { storeId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const { data: store } = useQuery({
    queryKey: ["store", storeId],
    queryFn: async () => (await api.get<Store>(`/stores/${storeId}`)).data,
  });

  const { data: invoices, isLoading } = useQuery({
    queryKey: ["invoices", storeId],
    queryFn: async () => (await api.get<Invoice[]>(`/stores/${storeId}/invoices`)).data,
  });

  const upload = useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      const { data } = await api.post<Invoice>(`/stores/${storeId}/invoices`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      // ننظّف تلقائياً بعد الرفع مباشرة — نفس تسلسل العمل الطبيعي، مع إبقاء
      // الرفع والتنظيف نقطتين منفصلتين بالباك إند (لو التنظيف فشل، الملف الخام محفوظ).
      try {
        await api.post(`/invoices/${data.id}/clean`);
      } catch {
        // فشل التنظيف يُعرض بشاشة المراجعة نفسها (زر "نظّف من جديد") — نكمل للتنقّل بدل ما نعلّق هنا
      }
      return data;
    },
    onSuccess: (invoice) => {
      queryClient.invalidateQueries({ queryKey: ["invoices", storeId] });
      navigate(`/invoices/${invoice.id}/review`);
    },
    onError: (err: any) => {
      setUploadError(err?.response?.data?.detail ?? "فشل رفع الملف");
    },
  });

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadError(null);
    upload.mutate(file);
    e.target.value = "";
  }

  return (
    <Layout>
      <div className="mb-1 text-sm">
        <Link to="/stores" className="text-slate-400 hover:text-slate-600">
          المتاجر
        </Link>
        <span className="mx-1.5 text-slate-300">/</span>
        <span className="font-medium text-slate-600">{store?.name ?? "..."}</span>
      </div>

      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-bold text-ink">فواتير {store?.name}</h1>
        <div className="flex items-center justify-between gap-4 sm:justify-end">
          <div className="flex items-center gap-4">
            <Link to={`/stores/${storeId}/inventory`} className="text-sm font-medium text-slate-500 hover:text-slate-700">
              المخزون
            </Link>
            <Link to={`/stores/${storeId}/history`} className="text-sm font-medium text-slate-500 hover:text-slate-700">
              السجل
            </Link>
          </div>
          <label className="cursor-pointer whitespace-nowrap rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700">
            {upload.isPending ? "...جار الرفع" : "+ رفع فاتورة"}
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx,.xls"
              onChange={handleFileChange}
              disabled={upload.isPending}
              className="hidden"
            />
          </label>
        </div>
      </div>

      {uploadError && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {uploadError}
        </div>
      )}

      {isLoading ? (
        <p className="text-sm text-slate-500">...جار التحميل</p>
      ) : !invoices?.length ? (
        <div className="rounded-xl border border-dashed border-slate-300 py-16 text-center text-sm text-slate-500">
          مافيش فواتير بعد — ارفع أول فاتورة عشان تبدأ.
        </div>
      ) : (
        <>
          {/* بطاقات للموبايل — جدول بأربعة أعمدة ما يتسع بعرض هاتف، بدل تمرير أفقي مزعج */}
          <div className="flex flex-col gap-3 sm:hidden">
            {invoices.map((inv) => (
              <button
                key={inv.id}
                onClick={() => navigate(nextStepPath(inv))}
                className="rounded-xl border border-slate-200 bg-white p-4 text-right transition hover:border-brand-300"
              >
                <div className="mb-2 flex items-start justify-between gap-3">
                  <span className="font-medium text-ink">{inv.original_filename ?? "—"}</span>
                  <StatusBadge status={inv.status} />
                </div>
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span>{inv.supplier_name_raw ?? "—"}</span>
                  <span className="font-mono">
                    {new Date(inv.uploaded_at).toLocaleDateString("ar-LY", { dateStyle: "medium" })}
                  </span>
                </div>
              </button>
            ))}
          </div>

          {/* جدول لعرض الشاشة الأكبر */}
          <div className="hidden overflow-x-auto rounded-xl border border-slate-200 bg-white sm:block">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-right text-xs font-medium text-slate-500">
                  <th className="px-4 py-3">الملف</th>
                  <th className="px-4 py-3">المورد</th>
                  <th className="px-4 py-3">الحالة</th>
                  <th className="px-4 py-3">تاريخ الرفع</th>
                </tr>
              </thead>
              <tbody>
                {invoices.map((inv) => (
                  <tr
                    key={inv.id}
                    onClick={() => navigate(nextStepPath(inv))}
                    className="cursor-pointer border-b border-slate-100 transition last:border-0 hover:bg-brand-50/40"
                  >
                    <td className="px-4 py-3 font-medium text-ink">{inv.original_filename ?? "—"}</td>
                    <td className="px-4 py-3 text-slate-500">{inv.supplier_name_raw ?? "—"}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={inv.status} />
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-400">
                      {new Date(inv.uploaded_at).toLocaleString("ar-LY", {
                        dateStyle: "medium",
                        timeStyle: "short",
                      })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </Layout>
  );
}
