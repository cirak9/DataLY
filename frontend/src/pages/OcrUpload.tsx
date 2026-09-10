import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { Invoice } from "../lib/types";
import Layout from "../components/Layout";

export default function OcrUpload() {
  const { storeId } = useParams();
  const navigate = useNavigate();
  const [files, setFiles] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);

  const upload = useMutation({
    mutationFn: async () => {
      const form = new FormData();
      files.forEach((f) => form.append("files", f));
      const { data } = await api.post<Invoice>(`/stores/${storeId}/invoices/ocr`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return data;
    },
    onSuccess: (invoice) => navigate(`/invoices/${invoice.id}/ocr-review`),
    onError: (err: any) => setError(err?.response?.data?.detail ?? "فشل رفع الصور"),
  });

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const picked = Array.from(e.target.files ?? []);
    if (!picked.length) return;
    setError(null);
    setFiles((prev) => [...prev, ...picked]);
    e.target.value = "";
  }

  function removeFile(index: number) {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }

  return (
    <Layout>
      <div className="mb-1 text-sm">
        <Link to={`/stores/${storeId}/invoices`} className="text-slate-400 hover:text-slate-600">
          الفواتير
        </Link>
        <span className="mx-1.5 text-slate-300">/</span>
        <span className="font-medium text-slate-600">رفع بالصور (OCR)</span>
      </div>

      <h1 className="mb-6 text-2xl font-bold text-ink">رفع فاتورة بالصور</h1>

      <div className="mb-4 rounded-lg border border-slate-200 bg-white p-4 text-sm leading-relaxed text-slate-500">
        صوّر الفاتورة بأكثر من صورة لو طويلة — كل الصور تُستخرَج معاً بمراجعة واحدة. بعد
        الرفع، الأصناف المستخرَجة تحتاج مراجعتك واعتمادك قبل ما تدخل خط المعالجة.
      </div>

      <label className="mb-4 flex cursor-pointer items-center justify-center rounded-xl border border-dashed border-slate-300 px-4 py-10 text-sm font-medium text-slate-600 transition hover:border-brand-400 hover:text-brand-600">
        📷 اختر صورة أو أكثر (jpg, png, webp)
        <input
          type="file"
          accept="image/jpeg,image/png,image/webp,image/gif"
          multiple
          onChange={handleFileChange}
          disabled={upload.isPending}
          className="hidden"
        />
      </label>

      {files.length > 0 && (
        <div className="mb-4 flex flex-col gap-2">
          {files.map((f, i) => (
            <div
              key={`${f.name}-${i}`}
              className="flex items-center justify-between rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
            >
              <span className="truncate text-slate-700">
                صورة {i + 1} — {f.name}
              </span>
              <button
                onClick={() => removeFile(i)}
                disabled={upload.isPending}
                className="shrink-0 rounded p-1 text-slate-300 transition hover:bg-red-50 hover:text-red-500"
                aria-label="إزالة"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <button
        onClick={() => upload.mutate()}
        disabled={files.length === 0 || upload.isPending}
        className="rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {upload.isPending ? "...جار الرفع" : `ارفع واستخرج (${files.length || 0} صورة) ←`}
      </button>
    </Layout>
  );
}
