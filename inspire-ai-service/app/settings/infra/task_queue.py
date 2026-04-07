from enum import StrEnum

from pydantic import BaseModel, Field


class TaskQueueType(StrEnum):
    CELERY = "celery"


class TaskQueueSettings(BaseModel):
    type: TaskQueueType = Field(default=TaskQueueType.CELERY)
    message_broker: str = Field(default="redis://localhost:6379/0")
    result_backend: str = Field(default="redis://localhost:6379/1")
    pool_type: str = Field(default="solo")
    max_tasks_per_child: str = Field(default="100")
    concurrency: str = Field(default="1")
    scheduled_hour: int = Field(default=2)
    scheduled_minute: int = Field(default=0)
