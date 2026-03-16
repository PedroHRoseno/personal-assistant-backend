from datetime import date, datetime, timedelta, timezone
import os

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text, func
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine
from .models import (
    Course,
    CoursePinnedLink,
    HomeTask,
    HomeTaskType,
    StudyPriority,
    StudyTask,
    TaskCategory,
    WorkHub,
    WorkHubLink,
    WorkTask,
)
from .schemas import (
    CourseCreate,
    CoursePinnedLinkCreate,
    CoursePinnedLinkRead,
    CourseRead,
    CourseReplace,
    CourseUpdate,
    HomeTaskCreate,
    HomeChecklistWidgetRead,
    HomeTaskRead,
    HomeTaskUpdate,
    StudyTaskCreate,
    StudyTaskRead,
    StudyTaskUpdate,
    UnifiedTaskRead,
    WorkHubCreate,
    WorkHubLinkCreate,
    WorkHubLinkRead,
    WorkHubRead,
    WorkHubReplace,
    WorkHubUpdate,
    WorkTaskCreate,
    WorkTaskRead,
    WorkTaskUpdate,
)

app = FastAPI(
    title="Productivity OS API",
    description="API do Productivity OS para Trabalho, Estudos e Casa.",
    version="0.3.0",
)

raw_cors = os.getenv("BACKEND_CORS_ORIGINS", "")
cors_origins = [origin.strip().rstrip("/") for origin in raw_cors.split(",") if origin.strip()]

# Para desenvolvimento local sem precisar de configuração extra.
if not cors_origins:
    cors_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def run_lightweight_migrations():
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "study_tasks" not in tables or "courses" not in tables:
        return

    study_columns = {column["name"] for column in inspector.get_columns("study_tasks")}
    with engine.begin() as connection:
        work_columns = {column["name"] for column in inspector.get_columns("work_tasks")}
        if "context_id" not in work_columns:
            connection.execute(text("ALTER TABLE work_tasks ADD COLUMN context_id INTEGER"))
        connection.execute(
            text(
                "UPDATE work_tasks SET due_date = due_date || ' 00:00:00' "
                "WHERE due_date IS NOT NULL AND LENGTH(due_date) = 10"
            )
        )
        connection.execute(
            text(
                "UPDATE home_tasks SET due_date = due_date || ' 00:00:00' "
                "WHERE due_date IS NOT NULL AND LENGTH(due_date) = 10"
            )
        )
        home_columns = {column["name"] for column in inspector.get_columns("home_tasks")}
        if "type" not in home_columns:
            connection.execute(text("ALTER TABLE home_tasks ADD COLUMN type VARCHAR(20)"))
        if "interval_days" not in home_columns:
            connection.execute(text("ALTER TABLE home_tasks ADD COLUMN interval_days INTEGER"))
        if "is_completed_today" not in home_columns:
            connection.execute(text("ALTER TABLE home_tasks ADD COLUMN is_completed_today BOOLEAN"))
        if "last_completed_at" not in home_columns:
            connection.execute(text("ALTER TABLE home_tasks ADD COLUMN last_completed_at DATETIME"))
        connection.execute(
            text(
                "UPDATE home_tasks SET type = CASE "
                "WHEN type IN ('diaria', 'DIARIA') THEN 'DIARIA' "
                "WHEN type IN ('ocasional', 'OCASIONAL') THEN 'OCASIONAL' "
                "WHEN type IN ('especifica', 'ESPECIFICA') THEN 'ESPECIFICA' "
                "ELSE 'DIARIA' END"
            )
        )
        connection.execute(
            text(
                "UPDATE home_tasks SET is_completed_today = CASE "
                "WHEN is_completed_today IS NULL THEN 0 "
                "ELSE is_completed_today END"
            )
        )
        if "course_id" not in study_columns:
            connection.execute(text("ALTER TABLE study_tasks ADD COLUMN course_id INTEGER"))
        connection.execute(
            text(
                "UPDATE study_tasks SET priority = CASE "
                "WHEN priority IN (1, '1', 'true', 'True', 'Alta', 'ALTA') THEN 'ALTA' "
                "WHEN priority IN (0, '0', 'false', 'False', '', 'Media', 'Média', 'MEDIA') THEN 'MEDIA' "
                "WHEN priority IN ('Baixa', 'BAIXA') THEN 'BAIXA' "
                "WHEN priority IS NULL THEN 'MEDIA' "
                "ELSE priority END"
            )
        )
        connection.execute(
            text(
                "UPDATE study_tasks SET due_date = due_date || ' 00:00:00' "
                "WHERE due_date IS NOT NULL AND LENGTH(due_date) = 10"
            )
        )
        course_columns = {column["name"] for column in inspector.get_columns("courses")}
        if "notes" not in course_columns:
            connection.execute(text("ALTER TABLE courses ADD COLUMN notes TEXT"))
        if "schedule" not in course_columns:
            connection.execute(text("ALTER TABLE courses ADD COLUMN schedule TEXT"))
        if "updated_at" not in course_columns:
            connection.execute(text("ALTER TABLE courses ADD COLUMN updated_at DATETIME"))
        connection.execute(
            text(
                "UPDATE courses SET schedule = '[]' "
                "WHERE schedule IS NULL OR TRIM(schedule) = '' OR SUBSTR(TRIM(schedule), 1, 1) <> '['"
            )
        )
        connection.execute(
            text("UPDATE courses SET updated_at = created_at WHERE updated_at IS NULL")
        )
        if "course_pinned_links" in tables:
            pinned_columns = {
                column["name"] for column in inspector.get_columns("course_pinned_links")
            }
            if "title" not in pinned_columns:
                connection.execute(
                    text("ALTER TABLE course_pinned_links ADD COLUMN title VARCHAR(140)")
                )
            if "label" in pinned_columns:
                connection.execute(
                    text(
                        "UPDATE course_pinned_links SET title = label "
                        "WHERE (title IS NULL OR title = '') AND label IS NOT NULL"
                    )
                )


def ensure_default_work_hubs():
    db = SessionLocal()
    try:
        if db.query(WorkHub).count() > 0:
            return
        db.add_all(
            [
                WorkHub(name="Software Dev", description="Hub para tarefas e notas de desenvolvimento."),
                WorkHub(name="Produção ALMotos", description="Hub operacional da produção ALMotos."),
                WorkHub(name="Gestão/Admin", description="Hub administrativo e de gestão."),
            ]
        )
        db.commit()
    finally:
        db.close()


run_lightweight_migrations()
ensure_default_work_hubs()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def reset_daily_home_tasks(db: Session):
    today = datetime.now(timezone.utc).date()
    daily_tasks = db.query(HomeTask).filter(HomeTask.task_type == HomeTaskType.DIARIA).all()
    changed = False
    for task in daily_tasks:
        last_day = task.last_completed.date() if task.last_completed else None
        if last_day != today and task.is_completed_today:
            task.is_completed_today = False
            task.status = "backlog"
            changed = True
    if changed:
        db.commit()


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/tasks/today", response_model=list[UnifiedTaskRead])
def list_today_tasks(db: Session = Depends(get_db)):
    today = date.today()

    work_tasks = (
        db.query(WorkTask)
        .filter((WorkTask.priority.is_(True)) | (func.date(WorkTask.due_date) == today.isoformat()))
        .order_by(WorkTask.created_at.desc())
        .all()
    )
    study_tasks = (
        db.query(StudyTask)
        .filter(
            (StudyTask.priority == StudyPriority.ALTA)
            | (func.date(StudyTask.due_date) == today.isoformat())
        )
        .order_by(StudyTask.created_at.desc())
        .all()
    )
    home_tasks = (
        db.query(HomeTask)
        .filter((HomeTask.priority.is_(True)) | (func.date(HomeTask.due_date) == today.isoformat()))
        .order_by(HomeTask.created_at.desc())
        .all()
    )

    response: list[UnifiedTaskRead] = []
    for task in work_tasks:
        response.append(
            UnifiedTaskRead(
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
        )
    for task in study_tasks:
        response.append(
            UnifiedTaskRead(
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
        )
    for task in home_tasks:
        response.append(
            UnifiedTaskRead(
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
        )
    return sorted(response, key=lambda task: (task.due_date is None, task.due_date, not task.priority))


@app.get("/tasks/all", response_model=list[UnifiedTaskRead])
def list_all_tasks(db: Session = Depends(get_db)):
    work_tasks = db.query(WorkTask).order_by(WorkTask.created_at.desc()).all()
    study_tasks = db.query(StudyTask).order_by(StudyTask.created_at.desc()).all()
    home_tasks = db.query(HomeTask).order_by(HomeTask.created_at.desc()).all()

    response: list[UnifiedTaskRead] = []
    for task in work_tasks:
        response.append(
            UnifiedTaskRead(
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
        )
    for task in study_tasks:
        response.append(
            UnifiedTaskRead(
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
        )
    for task in home_tasks:
        response.append(
            UnifiedTaskRead(
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
        )

    return sorted(response, key=lambda task: (task.due_date is None, task.due_date, task.created_at))


@app.get("/work-hubs", response_model=list[WorkHubRead])
def list_work_hubs(db: Session = Depends(get_db)):
    return db.query(WorkHub).order_by(WorkHub.id.asc()).all()


@app.post("/work-hubs", response_model=WorkHubRead, status_code=201)
def create_work_hub(payload: WorkHubCreate, db: Session = Depends(get_db)):
    hub = WorkHub(name=payload.name, description=payload.description)
    db.add(hub)
    db.commit()
    db.refresh(hub)
    return hub


@app.get("/work-hubs/{hub_id}", response_model=WorkHubRead)
def get_work_hub(hub_id: int, db: Session = Depends(get_db)):
    hub = db.query(WorkHub).filter(WorkHub.id == hub_id).first()
    if not hub:
        raise HTTPException(status_code=404, detail="Hub de trabalho não encontrado.")
    return hub


@app.patch("/work-hubs/{hub_id}", response_model=WorkHubRead)
def update_work_hub(hub_id: int, payload: WorkHubUpdate, db: Session = Depends(get_db)):
    hub = db.query(WorkHub).filter(WorkHub.id == hub_id).first()
    if not hub:
        raise HTTPException(status_code=404, detail="Hub de trabalho não encontrado.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(hub, field, value)
    db.commit()
    db.refresh(hub)
    return hub


@app.put("/work-hubs/{hub_id}", response_model=WorkHubRead)
def replace_work_hub(hub_id: int, payload: WorkHubReplace, db: Session = Depends(get_db)):
    hub = db.query(WorkHub).filter(WorkHub.id == hub_id).first()
    if not hub:
        raise HTTPException(status_code=404, detail="Hub de trabalho não encontrado.")

    hub.name = payload.name
    hub.description = payload.description
    hub.notes = payload.notes
    db.commit()
    db.refresh(hub)
    return hub


@app.post("/work-hubs/{hub_id}/links", response_model=WorkHubLinkRead, status_code=201)
def create_work_hub_link(hub_id: int, payload: WorkHubLinkCreate, db: Session = Depends(get_db)):
    hub = db.query(WorkHub).filter(WorkHub.id == hub_id).first()
    if not hub:
        raise HTTPException(status_code=404, detail="Hub de trabalho não encontrado.")

    link = WorkHubLink(hub_id=hub_id, title=payload.title, url=str(payload.url))
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


@app.delete("/work-hubs/{hub_id}/links/{link_id}", status_code=204)
def delete_work_hub_link(hub_id: int, link_id: int, db: Session = Depends(get_db)):
    link = db.query(WorkHubLink).filter(WorkHubLink.id == link_id, WorkHubLink.hub_id == hub_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link do hub não encontrado.")
    db.delete(link)
    db.commit()


@app.get("/work-tasks", response_model=list[WorkTaskRead])
def list_work_tasks(context_id: int | None = Query(default=None), db: Session = Depends(get_db)):
    query = db.query(WorkTask)
    if context_id is not None:
        query = query.filter(WorkTask.context_id == context_id)
    tasks = query.order_by(WorkTask.created_at.desc()).all()
    return [
        WorkTaskRead(
            id=task.id,
            title=task.title,
            description=task.description,
            status=task.status,
            priority=task.priority,
            due_date=task.due_date,
            context=task.context,
            label=task.label,
            context_id=task.context_id,
            context_name=task.work_hub.name if task.work_hub else None,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
        for task in tasks
    ]


@app.post("/work-tasks", response_model=WorkTaskRead, status_code=201)
def create_work_task(payload: WorkTaskCreate, db: Session = Depends(get_db)):
    if payload.context_id is not None:
        hub = db.query(WorkHub).filter(WorkHub.id == payload.context_id).first()
        if not hub:
            raise HTTPException(status_code=404, detail="Hub de trabalho não encontrado.")

    task = WorkTask(**payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return WorkTaskRead(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        due_date=task.due_date,
        context=task.context,
        label=task.label,
        context_id=task.context_id,
        context_name=task.work_hub.name if task.work_hub else None,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@app.patch("/work-tasks/{task_id}", response_model=WorkTaskRead)
def update_work_task(task_id: int, payload: WorkTaskUpdate, db: Session = Depends(get_db)):
    task = db.query(WorkTask).filter(WorkTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")

    if payload.context_id is not None:
        hub = db.query(WorkHub).filter(WorkHub.id == payload.context_id).first()
        if not hub:
            raise HTTPException(status_code=404, detail="Hub de trabalho não encontrado.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return WorkTaskRead(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        due_date=task.due_date,
        context=task.context,
        label=task.label,
        context_id=task.context_id,
        context_name=task.work_hub.name if task.work_hub else None,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@app.delete("/work-tasks/{task_id}", status_code=204)
def delete_work_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(WorkTask).filter(WorkTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
    db.delete(task)
    db.commit()


@app.get("/study-tasks", response_model=list[StudyTaskRead])
def list_study_tasks(course_id: int | None = Query(default=None), db: Session = Depends(get_db)):
    query = db.query(StudyTask)
    if course_id is not None:
        query = query.filter(StudyTask.course_id == course_id)
    tasks = query.order_by(StudyTask.created_at.desc()).all()
    return [
        StudyTaskRead(
            id=task.id,
            title=task.title,
            description=task.description,
            status=task.status,
            priority=task.priority,
            due_date=task.due_date,
            course_id=task.course_id,
            course_title=task.course.title if task.course else None,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
        for task in tasks
    ]


@app.post("/study-tasks", response_model=StudyTaskRead, status_code=201)
def create_study_task(payload: StudyTaskCreate, db: Session = Depends(get_db)):
    if payload.course_id is not None:
        course = db.query(Course).filter(Course.id == payload.course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="Curso não encontrado.")

    task = StudyTask(**payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return StudyTaskRead(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        due_date=task.due_date,
        course_id=task.course_id,
        course_title=task.course.title if task.course else None,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@app.patch("/study-tasks/{task_id}", response_model=StudyTaskRead)
def update_study_task(task_id: int, payload: StudyTaskUpdate, db: Session = Depends(get_db)):
    task = db.query(StudyTask).filter(StudyTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")

    if payload.course_id is not None:
        course = db.query(Course).filter(Course.id == payload.course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="Curso não encontrado.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return StudyTaskRead(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        due_date=task.due_date,
        course_id=task.course_id,
        course_title=task.course.title if task.course else None,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@app.delete("/study-tasks/{task_id}", status_code=204)
def delete_study_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(StudyTask).filter(StudyTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
    db.delete(task)
    db.commit()


@app.get("/courses", response_model=list[CourseRead])
def list_courses(db: Session = Depends(get_db)):
    return db.query(Course).order_by(Course.created_at.desc()).all()


@app.post("/courses", response_model=CourseRead, status_code=201)
def create_course(payload: CourseCreate, db: Session = Depends(get_db)):
    values = payload.model_dump()
    course = Course(
        title=values["title"],
        description=values.get("description"),
        schedule=values.get("schedule", []),
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@app.get("/courses/{course_id}", response_model=CourseRead)
def get_course(course_id: int, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Curso não encontrado.")
    return course


@app.patch("/courses/{course_id}", response_model=CourseRead)
def update_course(course_id: int, payload: CourseUpdate, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Curso não encontrado.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(course, field, value)
    db.commit()
    db.refresh(course)
    return course


@app.put("/courses/{course_id}", response_model=CourseRead)
def replace_course(course_id: int, payload: CourseReplace, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Curso não encontrado.")

    values = payload.model_dump()
    course.title = values["title"]
    course.description = values.get("description")
    course.notes = values.get("notes")
    course.schedule = values.get("schedule", [])
    db.commit()
    db.refresh(course)
    return course


@app.post("/courses/{course_id}/pinned-links", response_model=CoursePinnedLinkRead, status_code=201)
def create_pinned_link(course_id: int, payload: CoursePinnedLinkCreate, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Curso não encontrado.")

    link = CoursePinnedLink(course_id=course_id, title=payload.title, url=str(payload.url))
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


@app.delete("/courses/{course_id}/pinned-links/{link_id}", status_code=204)
def delete_pinned_link(course_id: int, link_id: int, db: Session = Depends(get_db)):
    link = (
        db.query(CoursePinnedLink)
        .filter(CoursePinnedLink.id == link_id, CoursePinnedLink.course_id == course_id)
        .first()
    )
    if not link:
        raise HTTPException(status_code=404, detail="Link fixado não encontrado.")
    db.delete(link)
    db.commit()


@app.get("/home-tasks", response_model=list[HomeTaskRead])
def list_home_tasks(db: Session = Depends(get_db)):
    reset_daily_home_tasks(db)
    return db.query(HomeTask).order_by(HomeTask.created_at.desc()).all()


@app.post("/home-tasks", response_model=HomeTaskRead, status_code=201)
def create_home_task(payload: HomeTaskCreate, db: Session = Depends(get_db)):
    task = HomeTask(**payload.model_dump())
    if task.task_type != HomeTaskType.OCASIONAL:
        task.recurrence_interval = None
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@app.patch("/home-tasks/{task_id}", response_model=HomeTaskRead)
def update_home_task(task_id: int, payload: HomeTaskUpdate, db: Session = Depends(get_db)):
    reset_daily_home_tasks(db)
    task = db.query(HomeTask).filter(HomeTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    if task.task_type != HomeTaskType.OCASIONAL:
        task.recurrence_interval = None

    changed_fields = payload.model_dump(exclude_unset=True)
    if "is_completed_today" in changed_fields and task.is_completed_today:
        task.last_completed = datetime.now(timezone.utc)
        if task.task_type == HomeTaskType.DIARIA:
            task.status = "concluido"

    if "status" in changed_fields and task.status == "concluido":
        task.last_completed = datetime.now(timezone.utc)
        if task.task_type == HomeTaskType.DIARIA:
            task.is_completed_today = True
        if task.task_type == HomeTaskType.OCASIONAL:
            days = task.recurrence_interval or 0
            if days > 0:
                task.due_date = datetime.now(timezone.utc) + timedelta(days=days)
            task.status = "backlog"
        if task.task_type == HomeTaskType.ESPECIFICA:
            task.is_completed_today = True

    if "status" in changed_fields and task.status != "concluido" and task.task_type == HomeTaskType.DIARIA:
        task.is_completed_today = False
    db.commit()
    db.refresh(task)
    return task


@app.delete("/home-tasks/{task_id}", status_code=204)
def delete_home_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(HomeTask).filter(HomeTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
    db.delete(task)
    db.commit()


@app.get("/home-tasks/checklist-today", response_model=list[HomeChecklistWidgetRead])
def home_checklist_today(db: Session = Depends(get_db)):
    reset_daily_home_tasks(db)
    today = date.today()
    tasks = db.query(HomeTask).order_by(HomeTask.created_at.asc()).all()

    result: list[HomeChecklistWidgetRead] = []
    for task in tasks:
        if task.task_type == HomeTaskType.DIARIA:
            result.append(
                HomeChecklistWidgetRead(
                    id=task.id,
                    title=task.title,
                    task_type=task.task_type,
                    due_date=task.due_date,
                    is_completed_today=task.is_completed_today,
                )
            )
            continue

        if task.task_type in (HomeTaskType.OCASIONAL, HomeTaskType.ESPECIFICA):
            if task.due_date and task.due_date.date() <= today and task.status != "concluido":
                result.append(
                    HomeChecklistWidgetRead(
                        id=task.id,
                        title=task.title,
                        task_type=task.task_type,
                        due_date=task.due_date,
                        is_completed_today=task.is_completed_today,
                    )
                )
    return result


@app.post("/home-tasks/reset-daily")
def reset_home_tasks_daily(db: Session = Depends(get_db)):
    reset_daily_home_tasks(db)
    return {"status": "ok"}
