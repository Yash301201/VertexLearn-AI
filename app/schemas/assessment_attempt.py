from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class SubmittedAnswer(BaseModel):
    question_id: int = Field(gt=0)
    selected_option_index: int = Field(ge=0)


class AssessmentAttemptCreate(BaseModel):
    answers: list[SubmittedAnswer] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_questions(self):
        question_ids = [answer.question_id for answer in self.answers]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("Each question can only be answered once")
        return self


class AssessmentAttemptResponse(BaseModel):
    id: int
    assessment_id: int
    user_id: int
    score: float
    passed: bool
    submitted_at: datetime