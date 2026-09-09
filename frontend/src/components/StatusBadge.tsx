import { InvoiceStatus, STATUS_LABELS } from "../lib/types";

const STYLES: Record<InvoiceStatus, string> = {
  uploaded: "bg-slate-100 text-slate-700",
  cleaned: "bg-brand-100 text-brand-700",
  session_pending: "bg-amber-100 text-amber-800",
  session_complete: "bg-amber-100 text-amber-800",
  reconciled: "bg-violet-100 text-violet-700",
  merged: "bg-emerald-100 text-emerald-700",
  exported: "bg-emerald-600 text-white",
};

export default function StatusBadge({ status }: { status: InvoiceStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold whitespace-nowrap ${STYLES[status]}`}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}
