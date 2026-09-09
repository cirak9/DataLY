from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.store import Store, Supplier
from app.schemas.store import StoreCreate, StoreOut, SupplierCreate, SupplierOut

router = APIRouter(tags=["stores"], dependencies=[Depends(get_current_user)])


@router.get("/stores", response_model=list[StoreOut])
def list_stores(db: Session = Depends(get_db)):
    return db.query(Store).order_by(Store.name).all()


@router.post("/stores", response_model=StoreOut, status_code=status.HTTP_201_CREATED)
def create_store(payload: StoreCreate, db: Session = Depends(get_db)):
    if db.query(Store).filter(Store.code == payload.code).first():
        raise HTTPException(status_code=400, detail="كود المتجر مستخدم مسبقاً")
    store = Store(name=payload.name, code=payload.code)
    db.add(store)
    db.commit()
    db.refresh(store)
    return store


@router.get("/suppliers", response_model=list[SupplierOut])
def list_suppliers(db: Session = Depends(get_db)):
    return db.query(Supplier).order_by(Supplier.name).all()


@router.post("/suppliers", response_model=SupplierOut, status_code=status.HTTP_201_CREATED)
def create_supplier(payload: SupplierCreate, db: Session = Depends(get_db)):
    existing = db.query(Supplier).filter(Supplier.name == payload.name).first()
    if existing:
        return existing
    supplier = Supplier(name=payload.name)
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier
