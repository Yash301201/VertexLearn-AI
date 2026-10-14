from typing import Optional

from pydantic import BaseModel, Field, model_validator


class AssessmentQuestionCreate(BaseModel):
    prompt: str = Field(min_length=5, max_length=4000)
    options: list[str] = Field(min_length=2, max_length=8)
    correct_option_index: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_correct_option(self):
        if self.correct_option_index >= len(self.options):
            raise ValueError("correct_option_index must refer to an option")
        if any(not option.strip() for option in self.options):
            raise ValueError("Options cannot be blank")
        return self


class AssessmentQuestionUpdate(BaseModel):
    prompt: Optional[str] = Field(None, min_length=5, max_length=4000)
    options: Optional[list[str]] = Field(None, min_length=2, max_length=8)
    correct_option_index: Optional[int] = Field(None, ge=0)


class AssessmentQuestionResponse(BaseModel):
    id: int
    assessment_id: int
    prompt: str
    options: list[str]
    position: int


class AdminAssessmentQuestionResponse(AssessmentQuestionResponse):
    correct_option_index: int