from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, HttpUrl

from .models import HomeTaskType, StudyPriority, TaskCategory, TaskStatus, WorkContext, WorkLabel


class BaseTaskFields(BaseModel):
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.BACKLOG
    priority: bool = False
    due_date: Optional[datetime] = None


class BaseTaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[bool] = None
    due_date: Optional[datetime] = None


class WorkTaskCreate(BaseTaskFields):
    context: WorkContext = WorkContext.PROGRAMACAO
    label: WorkLabel = WorkLabel.DEV
    context_id: Optional[int] = None


class WorkTaskUpdate(BaseTaskUpdate):
    context: Optional[WorkContext] = None
    label: Optional[WorkLabel] = None
    context_id: Optional[int] = None


class WorkTaskRead(BaseTaskFields):
    id: int
    context: WorkContext
    label: WorkLabel
    context_id: Optional[int] = None
    context_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StudyTaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.BACKLOG
    priority: StudyPriority = StudyPriority.MEDIA
    due_date: Optional[datetime] = None
    course_id: Optional[int] = None


class StudyTaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[StudyPriority] = None
    due_date: Optional[datetime] = None
    course_id: Optional[int] = None


class StudyTaskRead(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    status: TaskStatus
    priority: StudyPriority
    due_date: Optional[datetime] = None
    course_id: Optional[int] = None
    course_title: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class HomeTaskCreate(BaseTaskFields):
    zone: Optional[str] = None
    task_type: HomeTaskType = HomeTaskType.DIARIA
    recurrence_interval: Optional[int] = None
    is_completed_today: bool = False


class HomeTaskUpdate(BaseTaskUpdate):
    zone: Optional[str] = None
    task_type: Optional[HomeTaskType] = None
    recurrence_interval: Optional[int] = None
    is_completed_today: Optional[bool] = None


class HomeTaskRead(BaseTaskFields):
    id: int
    zone: Optional[str] = None
    task_type: HomeTaskType
    recurrence_interval: Optional[int] = None
    is_completed_today: bool
    last_completed: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class HomeChecklistWidgetRead(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: int
    title: str
    task_type: HomeTaskType
    due_date: Optional[datetime] = None
    is_completed_today: bool


class UnifiedTaskRead(BaseModel):
    id: int
    task_type: Literal["work", "study", "home"]
    category: TaskCategory
    title: str
    description: Optional[str] = None
    status: TaskStatus
    priority: bool
    due_date: Optional[date] = None
    context: Optional[WorkContext] = None
    context_id: Optional[int] = None
    context_name: Optional[str] = None
    label: Optional[WorkLabel] = None
    course_title: Optional[str] = None
    zone: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class WorkHubLinkCreate(BaseModel):
    title: str
    url: HttpUrl


class WorkHubLinkRead(BaseModel):
    id: int
    hub_id: int
    title: str
    url: str
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkHubCreate(BaseModel):
    name: str
    description: Optional[str] = None


class WorkHubUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None


class WorkHubReplace(BaseModel):
    name: str
    description: Optional[str] = None
    notes: Optional[str] = None


class WorkHubRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    notes: Optional[str] = None
    links: list[WorkHubLinkRead] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CoursePinnedLinkCreate(BaseModel):
    title: str
    url: HttpUrl


class CoursePinnedLinkRead(BaseModel):
    id: int
    course_id: int
    title: Optional[str] = None
    url: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CourseScheduleItem(BaseModel):
    day: str
    time: str


class CourseCreate(BaseModel):
    title: str
    description: Optional[str] = None
    schedule: list[CourseScheduleItem] = []


class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    schedule: Optional[list[CourseScheduleItem]] = None
    notes: Optional[str] = None


class CourseReplace(BaseModel):
    title: str
    description: Optional[str] = None
    notes: Optional[str] = None
    schedule: list[CourseScheduleItem] = []


class CourseRead(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    schedule: list[CourseScheduleItem] = []
    notes: Optional[str] = None
    pinned_links: list[CoursePinnedLinkRead] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
