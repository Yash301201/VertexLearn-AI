from typing import Optional

from pydantic import BaseModel, Field


class CourseCreate(BaseModel):
    title: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Title of the course"
    )

    description: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Detailed description of the course"
    )

    instructor: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Name of the course instructor"
    )


class CourseUpdate(BaseModel):
    title: Optional[str] = Field(
        None,
        min_length=3,
        max_length=200
    )

    description: Optional[str] = Field(
        None,
        min_length=10,
        max_length=2000
    )

    instructor: Optional[str] = Field(
        None,
        min_length=2,
        max_length=100
    )


class CourseResponse(BaseModel):
    id: int
    title: str
    description: str
    instructor: str