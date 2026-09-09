from app.schemas.invoice import InvoiceOut


class MergeResult(InvoiceOut):
    lots_upserted: int
    catalog_entries_learned: int
