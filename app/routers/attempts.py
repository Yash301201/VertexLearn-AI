from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.assessment import Assessment
from app.models.assessment_answer import AssessmentAnswer
from app.models.assessment_attempt import AssessmentAttempt
from app.models.assessment_question import AssessmentQuestion
from app.models.enrollment import Enrollment
from app.models.user import User
from app.routers.dependencies import get_admin_user, get_current_user
from app.schemas.assessment_attempt import (
    AssessmentAttemptCreate,
    AssessmentAttemptResponse,
)
from app.services.assessment_scoring import calculate_assessment_score

router = APIRouter(
    prefix="/attempts",
    tags=["Assessment Attempts"],
)


def _attempt_response(attempt: AssessmentAttempt) -> dict:
    return {
        "id": attempt.id,
        "assessment_id": attempt.assessment_id,
        "user_id": attempt.user_id,
        "score": attempt.score,
        "passed": attempt.passed,
        "submitted_at": attempt.submitted_at,
    }


@router.get("/", response_model=list[AssessmentAttemptResponse])
def get_all_attempts(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    attempts = db.scalars(
        select(AssessmentAttempt)
        .order_by(AssessmentAttempt.submitted_at.desc(), AssessmentAttempt.id.desc())
        .limit(limit)
    )
    return [_attempt_response(attempt) for attempt in attempts]


@router.get("/me", response_model=list[AssessmentAttemptResponse])
def get_my_attempts(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attempts = db.scalars(
        select(AssessmentAttempt)
        .where(AssessmentAttempt.user_id == current_user.id)
        .order_by(AssessmentAttempt.submitted_at.desc(), AssessmentAttempt.id.desc())
        .limit(limit)
    )
    return [_attempt_response(attempt) for attempt in attempts]


@router.post(
    "/assessments/{assessment_id}",
    response_model=AssessmentAttemptResponse,
    status_code=201,
)
def submit_assessment_attempt(
    assessment_id: int,
    submission: AssessmentAttemptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assessment = db.get(Assessment, assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")

    if current_user.role != "admin":
        enrollment = db.scalar(
            select(Enrollment.id).where(
                Enrollment.user_id == current_user.id,
                Enrollment.course_id == assessment.course_id,
            )
        )
        if enrollment is None:
            raise HTTPException(status_code=403, detail="Enroll in this course before attempting")

    questions = list(
        db.scalars(
            select(AssessmentQuestion)
            .where(AssessmentQuestion.assessment_id == assessment_id)
            .order_by(AssessmentQuestion.position, AssessmentQuestion.id)
        )
    )
    if not questions:
        raise HTTPException(status_code=409, detail="This assessment has no questions yet")

    selected_options = {
        answer.question_id: answer.selected_option_index
        for answer in submission.answers
    }
    question_ids = {question.id for question in questions}
    if set(selected_options) != question_ids:
        raise HTTPException(
            status_code=422,
            detail="Submit exactly one answer for every assessment question",
        )
    for question in questions:
        if selected_options[question.id] >= len(question.options):
            raise HTTPException(
                status_code=422,
                detail=f"Selected option is invalid for question {question.id}",
            )

    score, passed, correctness = calculate_assessment_score(
        questions,
        selected_options,
        assessment.passing_score,
    )
    attempt = AssessmentAttempt(
        assessment_id=assessment_id,
        user_id=current_user.id,
        score=score,
        passed=passed,
    )
    db.add(attempt)
    db.flush()
    db.add_all(
        [
            AssessmentAnswer(
                attempt_id=attempt.id,
                question_id=question.id,
                selected_option_index=selected_options[question.id],
                is_correct=correctness[question.id],
            )
            for question in questions
        ]
    )
    db.commit()
    db.refresh(attempt)
    return _attempt_response(attempt)


@router.get("/{attempt_id}", response_model=AssessmentAttemptResponse)
def get_attempt(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attempt = db.get(AssessmentAttempt, attempt_id)
    if attempt is None:
        raise HTTPException(status_code=404, detail="Assessment attempt not found")
    if current_user.id != attempt.user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="You can only view your own attempts")
    return _attempt_response(attempt)