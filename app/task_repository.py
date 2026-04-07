"""Helpers genéricos para CRUD mínimo (evita repetir query+delete em cada endpoint)."""

from typing import TypeVar

from sqlalchemy.orm import Session

from .database import Base

ModelT = TypeVar("ModelT", bound=Base)


def delete_by_id(db: Session, model: type[ModelT], entity_id: int) -> bool:
    """Remove uma entidade por id. Retorna True se existia."""
    entity = db.query(model).filter(model.id == entity_id).first()
    if not entity:
        return False
    db.delete(entity)
    db.commit()
    return True
