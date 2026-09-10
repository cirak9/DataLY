from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_owned_store
from app.core.db import get_db
from app.core_logic.inventory_extractor import InventoryImportError
from app.models.inventory import InventoryLot
from app.models.store import Store
from app.schemas.inventory import InventoryImportResult, InventoryLotOut
from app.services import inventory_import_service

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


@router.post("/stores/{store_id}/inventory/import", response_model=InventoryImportResult, status_code=status.HTTP_201_CREATED)
async def import_store_inventory(
    file: UploadFile, store: Store = Depends(get_owned_store), db: Session = Depends(get_db)
):
    content = await file.read()
    try:
        return inventory_import_service.import_old_inventory(db, store, file.filename, content)
    except InventoryImportError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
