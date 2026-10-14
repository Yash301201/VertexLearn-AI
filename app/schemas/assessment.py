from typing import Optional

from pydantic import BaseModel, Field


class AssessmentCreate(BaseModel):
    title: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Title of the assessment"
    )

    course_id: int = Field(
        ...,
        gt=0,
        description="ID of the course"
    )

    total_questions: int = Field(
        ...,
        gt=0,
        description="Total number of questions"
    )

    passing_score: float = Field(
        ...,
        ge=0,
        le=100,
        description="Minimum percentage required to pass"
    )


class AssessmentUpdate(BaseModel):
    title: Optional[str] = Field(
        None,
        min_length=3,
        max_length=200
    )

    total_questions: Optional[int] = Field(
        None,
        gt=0
    )

    passing_score: Optional[float] = Field(
        None,
        ge=0,
        le=100
    )

    course_id: Optional[int] = Field(
        None,
        gt=0
    )


class AssessmentResponse(BaseModel):
    id: int
    title: str
    course_id: int
    total_questions: int
    passing_score: float