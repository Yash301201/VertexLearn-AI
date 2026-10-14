from datetime import datetime

from pydantic import BaseModel, EmailStr


class EnrollmentResponse(BaseModel):
    id: int
    course_id: int
    course_title: str
    enrolled_at: datetime
    progress_percent: float


class AdminEnrollmentResponse(EnrollmentResponse):
    user_id: int
    user_name: str
    user_email: EmailStr