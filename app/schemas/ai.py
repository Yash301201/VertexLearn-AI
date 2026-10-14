from pydantic import BaseModel, Field


class AIStudyRequest(BaseModel):
	course_id: int = Field(..., gt=0)
	question: str = Field(..., min_length=5, max_length=2000)