"""Consultas reutilizáveis para tarefas (joinedload + filtros), usadas em /tasks/today e workers paralelos."""

from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from .models import HomeTask, StudyPriority, StudyTask, WorkTask


def query_today_work_tasks(db: Session, today: date) -> list[WorkTask]:
    return (
        db.query(WorkTask)
        .options(joinedload(WorkTask.work_hub))
        .filter((WorkTask.priority.is_(True)) | (func.date(WorkTask.due_date) == today.isoformat()))
        .order_by(WorkTask.created_at.desc())
        .all()
    )


def query_today_study_tasks(db: Session, today: date) -> list[StudyTask]:
    return (
        db.query(StudyTask)
        .options(joinedload(StudyTask.course))
        .filter(
            (StudyTask.priority == StudyPriority.ALTA)
            | (func.date(StudyTask.due_date) == today.isoformat())
        )
        .order_by(StudyTask.created_at.desc())
        .all()
    )


def query_today_home_tasks(db: Session, today: date) -> list[HomeTask]:
    return (
        db.query(HomeTask)
        .filter((HomeTask.priority.is_(True)) | (func.date(HomeTask.due_date) == today.isoformat()))
        .order_by(HomeTask.created_at.desc())
        .all()
    )


def query_all_work_tasks(db: Session) -> list[WorkTask]:
    return db.query(WorkTask).options(joinedload(WorkTask.work_hub)).order_by(WorkTask.created_at.desc()).all()


def query_all_study_tasks(db: Session) -> list[StudyTask]:
    return db.query(StudyTask).options(joinedload(StudyTask.course)).order_by(StudyTask.created_at.desc()).all()


def query_all_home_tasks(db: Session) -> list[HomeTask]:
    return db.query(HomeTask).order_by(HomeTask.created_at.desc()).all()
