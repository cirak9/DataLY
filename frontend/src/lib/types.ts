export interface Store {
  id: number;
  name: string;
  code: string;
}

export type InvoiceStatus =
  | "uploaded"
  | "cleaned"
  | "session_pending"
  | "session_complete"
  | "reconciled"
  | "merged"
  | "exported";

export interface Invoice {
  id: number;
  store_id: number;
  supplier_id: number | null;
  supplier_name_raw: string | null;
  method: number;
  status: InvoiceStatus;
  original_filename: string | null;
  uploaded_at: string;
}

export interface CategoryOut {
  id: number;
  main: string;
  sub: string;
}

export interface InvoiceItem {
  id: number;
  invoice_id: number;
  item_order: number;
  item_name: string;
  category_id: number | null;
  category: CategoryOut | null;
  unit_text: string | null;
  quantity_pieces: number;
  per_box: number | null;
  box_count: number | null;
  unit_cost: number | null;
  total_price: number | null;
  discount_pct: number | null;
  expiry_date: string | null;
  supplier_item_code: string | null;
  barcode: string | null;
}

export interface SessionItem {
  id: number;
  session_id: number;
  invoice_item_id: number;
  item_name: string;
  unit_cost: number | null;
  barcode: string | null;
  expiration_date: string | null;
  sale_price: number | null;
  is_complete: boolean;
}

export interface IntakeSession {
  id: number;
  invoice_id: number;
  method: number;
  status: "pending" | "complete";
  created_at: string;
  completed_at: string | null;
  items: SessionItem[];
}

export interface ReconciliationMatch {
  id: number;
  invoice_item_id: number;
  item_name: string;
  match_method: "barcode" | "fuzzy_name";
  matched_barcode: string | null;
  suggested_name: string | null;
  suggested_category_id: number | null;
  similarity_score: number | null;
  warning_reason: string | null;
  decision: "pending" | "approved" | "rejected" | "manual";
  manual_name: string | null;
  decided_at: string | null;
}

export interface MergeResult extends Invoice {
  lots_upserted: number;
  catalog_entries_learned: number;
}

export interface AlsahlExport {
  id: number;
  invoice_id: number;
  exported_at: string;
}

export interface InventoryLot {
  id: number;
  barcode: string;
  item_name: string | null;
  expiration_date: string | null;
  quantity: number | null;
  unit_cost: number | null;
  updated_at: string;
}

export const STATUS_LABELS: Record<InvoiceStatus, string> = {
  uploaded: "مرفوعة",
  cleaned: "منظّفة",
  session_pending: "بانتظار الاستلام",
  session_complete: "استلام مكتمل",
  reconciled: "مُسوّاة",
  merged: "مدموجة",
  exported: "مُصدَّرة",
};
