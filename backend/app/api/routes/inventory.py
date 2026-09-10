from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_owned_store
from app.core.db import get_db
from app.models.inventory import InventoryLot
from app.models.store import Store
from app.schemas.inventory import InventoryLotOut

router = APIRouter(tags=["inventory"], dependencies=[Depends(get_current_user)])


@router.get("/stores/{store_id}/inventory", response_model=list[InventoryLotOut])
def list_store_inventory(store: Store = Depends(get_owned_store), db: Session = Depends(get_db)):
    # الأقرب انتهاءً أولاً (NULL آخر شي) — يساعد بمتابعة الأصناف المهدَّدة بالهدر قبل غيرها.
    return (
        db.query(InventoryLot)
        .filter(InventoryLot.store_id == store.id)
        .order_by(InventoryLot.expiration_date.is_(None), InventoryLot.expiration_date.asc())
        .all()
    )
