import enum

from sqlalchemy import JSON, Boolean, Column, DateTime, Enum, Integer, String, Text, func
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

from .database import Base


class TaskStatus(str, enum.Enum):
    BACKLOG = "backlog"
    EM_FAZENDO = "em_fazendo"
    CONCLUIDO = "concluido"


class TaskCategory(str, enum.Enum):
    TRABALHO = "trabalho"
    ESTUDOS = "estudos"
    CASA = "casa"


class HomeTaskType(str, enum.Enum):
    DIARIA = "diaria"
    OCASIONAL = "ocasional"
    ESPECIFICA = "especifica"


class WorkContext(str, enum.Enum):
    PROGRAMACAO = "programacao"
    ALMOTOS = "almotos"
    GESTAO_ADMIN = "gestao_admin"


class WorkLabel(str, enum.Enum):
    DEV = "dev"
    CONTEUDO = "conteudo"


class StudyPriority(str, enum.Enum):
    ALTA = "Alta"
    MEDIA = "Média"
    BAIXA = "Baixa"


class BaseTaskMixin:
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(160), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(TaskStatus), nullable=False, default=TaskStatus.BACKLOG, index=True)
    priority = Column(Boolean, default=False, nullable=False, index=True)
    due_date = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class WorkTask(Base, BaseTaskMixin):
    __tablename__ = "work_tasks"

    context = Column(Enum(WorkContext), nullable=False, default=WorkContext.PROGRAMACAO, index=True)
    label = Column(Enum(WorkLabel), nullable=False, default=WorkLabel.DEV, index=True)
    context_id = Column(Integer, ForeignKey("work_hubs.id", ondelete="SET NULL"), nullable=True, index=True)

    work_hub = relationship("WorkHub", back_populates="tasks")


class StudyTask(Base, BaseTaskMixin):
    __tablename__ = "study_tasks"

    priority = Column(Enum(StudyPriority), nullable=False, default=StudyPriority.MEDIA, index=True)
    due_date = Column(DateTime(timezone=True), nullable=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="SET NULL"), nullable=True, index=True)

    course = relationship("Course", back_populates="study_tasks")


class HomeTask(Base, BaseTaskMixin):
    __tablename__ = "home_tasks"

    zone = Column(String(80), nullable=True)
    task_type = Column("type", Enum(HomeTaskType), nullable=False, default=HomeTaskType.DIARIA, index=True)
    recurrence_interval = Column("interval_days", Integer, nullable=True)
    is_completed_today = Column(Boolean, nullable=False, default=False, index=True)
    last_completed = Column("last_completed_at", DateTime(timezone=True), nullable=True)


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(160), nullable=False)
    description = Column(Text, nullable=True)
    schedule = Column(JSON, nullable=False, default=list)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    pinned_links = relationship(
        "CoursePinnedLink",
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="CoursePinnedLink.id.desc()",
    )
    study_tasks = relationship("StudyTask", back_populates="course")


class CoursePinnedLink(Base):
    __tablename__ = "course_pinned_links"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(140), nullable=True)
    url = Column(String(600), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    course = relationship("Course", back_populates="pinned_links")


class WorkHub(Base):
    __tablename__ = "work_hubs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    links = relationship(
        "WorkHubLink",
        back_populates="hub",
        cascade="all, delete-orphan",
        order_by="WorkHubLink.id.desc()",
    )
    tasks = relationship("WorkTask", back_populates="work_hub")


class WorkHubLink(Base):
    __tablename__ = "work_hub_links"

    id = Column(Integer, primary_key=True, index=True)
    hub_id = Column(Integer, ForeignKey("work_hubs.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(140), nullable=False)
    url = Column(String(600), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    hub = relationship("WorkHub", back_populates="links")
