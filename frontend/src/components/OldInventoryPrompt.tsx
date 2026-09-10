import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "../lib/api";
import { InventoryImportResult } from "../lib/types";

// يظهر قبل كل جلسة استلام جديدة — التاجر يقرر هو (النظام ما يقدر يكتشف تلقائياً
// إضافات مخزون يدوية صارت بدون فاتورة عبرنا)، فالسؤال صريح بكل مرة بدل تخمين متى
// يلزم. "تخطّي" مسموح دايماً — هالخطوة اختيارية، مو قفل.
export default function OldInventoryPrompt({
  storeId,
  onProceed,
}: {
  storeId: number;
  onProceed: () => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<InventoryImportResult | null>(null);

  const importMutation = useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      const { data } = await api.post<InventoryImportResult>(
        `/stores/${storeId}/inventory/import`,
        form,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      return data;
    },
    onSuccess: (data) => {
      setError(null);
      setResult(data);
    },
    onError: (err: any) => setError(err?.response?.data?.detail ?? "فشل استيراد المخزون"),
  });

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);
    setResult(null);
    importMutation.mutate(file);
    e.target.value = "";
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-lg">
        <h2 className="mb-2 text-lg font-bold text-ink">تحديث المخزون قبل الاستلام</h2>
        <p className="mb-4 text-sm leading-relaxed text-slate-500">
          هل أضفت أصناف مخزون يدوياً (بدون فاتورة عبرنا) منذ آخر مرة؟ ارفع ملف مخزونك
          الحالي عشان نحدّث سجلاتنا قبل ما نكمل — أو تخطَّ هالخطوة لو ما فيه شي تغيّر.
        </p>

        {result ? (
          <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
            تم استيراد {result.lots_processed} صنف بنجاح.
          </div>
        ) : (
          <label className="mb-4 flex cursor-pointer items-center justify-center rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm font-medium text-slate-600 transition hover:border-brand-400 hover:text-brand-600">
            {importMutation.isPending ? "...جار الاستيراد" : "📂 اختر ملف المخزون (xlsx)"}
            <input
              type="file"
              accept=".xlsx,.xls"
              onChange={handleFileChange}
              disabled={importMutation.isPending}
              className="hidden"
            />
          </label>
        )}

        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="flex justify-end gap-2">
          {!result && (
            <button
              onClick={onProceed}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
            >
              تخطّي والمتابعة
            </button>
          )}
          {result && (
            <button
              onClick={onProceed}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
            >
              متابعة إلى الاستلام ←
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
