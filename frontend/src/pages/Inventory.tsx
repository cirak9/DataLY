import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { InventoryLot, Store } from "../lib/types";
import Layout from "../components/Layout";

const DAY_MS = 1000 * 60 * 60 * 24;

function ExpiryBadge({ date }: { date: string | null }) {
  if (!date) {
    return <span className="text-xs text-slate-300">—</span>;
  }
  const days = Math.floor((new Date(date).getTime() - Date.now()) / DAY_MS);
  const formatted = new Date(date).toLocaleDateString("ar-LY", { dateStyle: "medium" });

  if (days < 0) {
    return (
      <span className="inline-flex items-center gap-1.5">
        <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-700">منتهي</span>
        <span className="font-mono text-xs text-slate-400">{formatted}</span>
      </span>
    );
  }
  if (days <= 30) {
    return (
      <span className="inline-flex items-center gap-1.5">
        <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-700">
          بعد {days} يوم
        </span>
        <span className="font-mono text-xs text-slate-400">{formatted}</span>
      </span>
    );
  }
  return <span className="font-mono text-xs text-slate-500">{formatted}</span>;
}

export default function Inventory() {
  const { storeId } = useParams();
  const [search, setSearch] = useState("");

  const { data: store } = useQuery({
    queryKey: ["store", storeId],
    queryFn: async () => (await api.get<Store>(`/stores/${storeId}`)).data,
  });

  const { data: lots, isLoading } = useQuery({
    queryKey: ["inventory", storeId],
    queryFn: async () => (await api.get<InventoryLot[]>(`/stores/${storeId}/inventory`)).data,
  });

  const filtered = useMemo(() => {
    if (!lots) return [];
    const q = search.trim().toLowerCase();
    if (!q) return lots;
    return lots.filter(
      (l) => l.item_name?.toLowerCase().includes(q) || l.barcode.toLowerCase().includes(q)
    );
  }, [lots, search]);

  return (
    <Layout>
      <div className="mb-1 text-sm">
        <Link to="/stores" className="text-slate-400 hover:text-slate-600">
          المتاجر
        </Link>
        <span className="mx-1.5 text-slate-300">/</span>
        <span className="font-medium text-slate-600">{store?.name ?? "..."}</span>
      </div>

      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-ink">مخزون {store?.name}</h1>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="بحث بالاسم أو الباركود..."
          className="w-64 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
        />
      </div>

      {isLoading ? (
        <p className="text-sm text-slate-500">...جار التحميل</p>
      ) : !lots?.length ? (
        <div className="rounded-xl border border-dashed border-slate-300 py-16 text-center text-sm text-slate-500">
          المخزون فاضي بعد — يتكوّن تلقائياً من دمج الفواتير.
        </div>
      ) : !filtered.length ? (
        <div className="rounded-xl border border-dashed border-slate-300 py-16 text-center text-sm text-slate-500">
          ما فيه نتائج تطابق البحث.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-right text-xs font-medium text-slate-500">
                <th className="px-4 py-3">الصنف</th>
                <th className="px-4 py-3">الباركود</th>
                <th className="px-4 py-3">الصلاحية</th>
                <th className="px-4 py-3">الكمية</th>
                <th className="px-4 py-3">تكلفة الوحدة</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((lot) => (
                <tr key={lot.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-4 py-3 font-medium text-ink">{lot.item_name ?? "—"}</td>
                  <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-slate-500">{lot.barcode}</td>
                  <td className="whitespace-nowrap px-4 py-3">
                    <ExpiryBadge date={lot.expiration_date} />
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-slate-600">
                    {lot.quantity ?? "—"}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-slate-600">
                    {lot.unit_cost ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Layout>
  );
}
