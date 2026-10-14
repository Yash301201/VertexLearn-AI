from typing import Optional

from pydantic import BaseModel, Field


class LessonCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    content: str = Field(min_length=1, max_length=20000)


class LessonUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    content: Optional[str] = Field(None, min_length=1, max_length=20000)
    position: Optional[int] = Field(None, ge=1)


class LessonResponse(BaseModel):
    id: int
    course_id: int
    title: str
    content: str
    position: int


class LessonCompletionResponse(BaseModel):
    course_id: int
    lesson_id: int
    completed: bool
    progress_percent: float