"""Serialização DRY de tarefas ORM → UnifiedTaskRead (usado em /tasks/today e /tasks/all)."""

from .models import HomeTask, StudyPriority, StudyTask, TaskCategory, WorkTask
from .schemas import UnifiedTaskRead


def work_task_to_unified(task: WorkTask) -> UnifiedTaskRead:
    return UnifiedTaskRead(
        id=task.id,
        task_type="work",
        category=TaskCategory.TRABALHO,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        due_date=task.due_date.date() if task.due_date else None,
        context=task.context,
        context_id=task.context_id,
        context_name=task.work_hub.name if task.work_hub else None,
        label=task.label,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def study_task_to_unified(task: StudyTask) -> UnifiedTaskRead:
    return UnifiedTaskRead(
        id=task.id,
        task_type="study",
        category=TaskCategory.ESTUDOS,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority == StudyPriority.ALTA,
        due_date=task.due_date.date() if task.due_date else None,
        course_title=task.course.title if task.course else None,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def home_task_to_unified(task: HomeTask) -> UnifiedTaskRead:
    return UnifiedTaskRead(
        id=task.id,
        task_type="home",
        category=TaskCategory.CASA,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        due_date=task.due_date.date() if task.due_date else None,
        zone=task.zone,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )
