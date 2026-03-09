#!/usr/bin/env python
# MODIFIED: 2026-03-03 - Added workers and equipment CRUD API
"""Resources API. Workers and equipment."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db, RequirePMOrAdmin, RequireAdmin, CurrentUser
from app.db.models import Worker, Equipment
from app.schemas.resource import (
    WorkerCreate,
    WorkerResponse,
    EquipmentCreate,
    EquipmentResponse,
)

router = APIRouter(prefix="/resources", tags=["resources"])


@router.get("/workers", response_model=list[WorkerResponse])
def worker_list(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
  return db.query(Worker).order_by(Worker.name).all()


@router.post("/workers", response_model=WorkerResponse)
def worker_create(
    data: WorkerCreate,
    current_user: RequirePMOrAdmin,
    db: Session = Depends(get_db),
):
  worker = Worker(
      name=data.name,
      trade=data.trade,
      hourly_rate=data.hourly_rate,
      phone=data.phone,
      email=data.email,
      availability=data.availability,
  )
  db.add(worker)
  db.commit()
  db.refresh(worker)
  return worker


@router.put("/workers/{worker_id}", response_model=WorkerResponse)
def worker_update(
    worker_id: int,
    data: WorkerCreate,
    current_user: RequirePMOrAdmin,
    db: Session = Depends(get_db),
):
  worker = db.query(Worker).filter(Worker.id == worker_id).first()
  if not worker:
      raise HTTPException(status_code=404, detail="Worker not found")
  worker.name = data.name
  worker.trade = data.trade
  worker.hourly_rate = data.hourly_rate
  worker.phone = data.phone
  worker.email = data.email
  worker.availability = data.availability
  db.commit()
  db.refresh(worker)
  return worker


@router.delete("/workers/{worker_id}")
def worker_delete(
    worker_id: int,
    current_user: RequirePMOrAdmin,
    db: Session = Depends(get_db),
):
  worker = db.query(Worker).filter(Worker.id == worker_id).first()
  if not worker:
      raise HTTPException(status_code=404, detail="Worker not found")
  db.delete(worker)
  db.commit()
  return {"message": "Deleted"}


@router.get("/equipment", response_model=list[EquipmentResponse])
def equipment_list(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
  return db.query(Equipment).order_by(Equipment.name).all()


@router.post("/equipment", response_model=EquipmentResponse)
def equipment_create(
    data: EquipmentCreate,
    current_user: RequirePMOrAdmin,
    db: Session = Depends(get_db),
):
  eq = Equipment(
      name=data.name,
      type=data.type,
      daily_cost=data.daily_cost,
      status=data.status,
  )
  db.add(eq)
  db.commit()
  db.refresh(eq)
  return eq


@router.put("/equipment/{equipment_id}", response_model=EquipmentResponse)
def equipment_update(
    equipment_id: int,
    data: EquipmentCreate,
    current_user: RequirePMOrAdmin,
    db: Session = Depends(get_db),
):
  eq = db.query(Equipment).filter(Equipment.id == equipment_id).first()
  if not eq:
      raise HTTPException(status_code=404, detail="Equipment not found")
  eq.name = data.name
  eq.type = data.type
  eq.daily_cost = data.daily_cost
  eq.status = data.status
  db.commit()
  db.refresh(eq)
  return eq


@router.delete("/equipment/{equipment_id}")
def equipment_delete(
    equipment_id: int,
    current_user: RequirePMOrAdmin,
    db: Session = Depends(get_db),
):
  eq = db.query(Equipment).filter(Equipment.id == equipment_id).first()
  if not eq:
      raise HTTPException(status_code=404, detail="Equipment not found")
  db.delete(eq)
  db.commit()
  return {"message": "Deleted"}

