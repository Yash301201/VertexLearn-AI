import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.assessment import Assessment as AssessmentModel
from app.models.assessment_attempt import AssessmentAttempt
from app.models.assessment_question import AssessmentQuestion
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.user import User
from app.routers.dependencies import get_admin_user, get_current_user
from app.schemas.assessment import AssessmentCreate, AssessmentUpdate
from app.schemas.assessment_question import (
    AssessmentQuestionCreate,
    AssessmentQuestionUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/assessments",
    tags=["Assessments"]
)


@router.get("/")
def get_assessments(db: Session = Depends(get_db)):
    logger.info("Fetching all assessments")
    assessments = list(
        db.scalars(select(AssessmentModel).order_by(AssessmentModel.id))
    )
    question_counts = dict(
        db.execute(
            select(
                AssessmentQuestion.assessment_id,
                func.count(AssessmentQuestion.id),
            ).group_by(AssessmentQuestion.assessment_id)
        ).all()
    )
    return {
        "message": "Assessments API is working",
        "assessments": [
            {
                "id": assessment.id,
                "title": assessment.title,
                "course_id": assessment.course_id,
                "total_questions": assessment.total_questions,
                "question_count": question_counts.get(assessment.id, 0),
                "ready": (
                    question_counts.get(assessment.id, 0) > 0
                    and question_counts.get(assessment.id, 0)
                    == assessment.total_questions
                ),
                "passing_score": assessment.passing_score,
            }
            for assessment in assessments
        ],
    }


@router.get("/{assessment_id}")
def get_assessment(assessment_id: int, db: Session = Depends(get_db)):
    logger.info("Fetching assessment with id=%s", assessment_id)
    assessment = db.get(AssessmentModel, assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return {
        "message": "Assessment details",
        "assessment": {
            "id": assessment.id,
            "title": assessment.title,
            "course_id": assessment.course_id,
            "total_questions": assessment.total_questions,
            "passing_score": assessment.passing_score,
        },
    }


@router.post("/")
def create_assessment(
    assessment: AssessmentCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    logger.info(
        "Creating assessment title=%s course_id=%s total_questions=%s",
        assessment.title,
        assessment.course_id,
        assessment.total_questions,
    )
    if db.get(Course, assessment.course_id) is None:
        raise HTTPException(status_code=404, detail="Course not found")

    db_assessment = AssessmentModel(**assessment.model_dump())
    db.add(db_assessment)
    db.commit()
    db.refresh(db_assessment)
    return {
        "message": "Assessment created successfully",
        "assessment": {
            "id": db_assessment.id,
            "title": db_assessment.title,
            "course_id": db_assessment.course_id,
            "total_questions": db_assessment.total_questions,
            "passing_score": db_assessment.passing_score,
        },
    }


@router.patch("/{assessment_id}")
def update_assessment(
    assessment_id: int,
    assessment_update: AssessmentUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    db_assessment = db.get(AssessmentModel, assessment_id)
    if db_assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")

    updates = assessment_update.model_dump(exclude_unset=True, exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="At least one field must be provided")

    question_count = db.scalar(
        select(func.count(AssessmentQuestion.id)).where(
            AssessmentQuestion.assessment_id == assessment_id
        )
    ) or 0
    if (
        question_count
        and "total_questions" in updates
        and updates["total_questions"] != question_count
    ):
        raise HTTPException(
            status_code=409,
            detail="total_questions is managed by the assessment questions",
        )

    new_course_id = updates.get("course_id")
    if new_course_id is not None and db.get(Course, new_course_id) is None:
        raise HTTPException(status_code=404, detail="Course not found")

    for field, value in updates.items():
        setattr(db_assessment, field, value)

    db.commit()
    db.refresh(db_assessment)
    return {
        "message": "Assessment updated successfully",
        "assessment": {
            "id": db_assessment.id,
            "title": db_assessment.title,
            "course_id": db_assessment.course_id,
            "total_questions": db_assessment.total_questions,
            "passing_score": db_assessment.passing_score,
        },
    }


@router.delete("/{assessment_id}")
def delete_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    db_assessment = db.get(AssessmentModel, assessment_id)
    if db_assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")

    db.delete(db_assessment)
    db.commit()
    return {"message": "Assessment deleted successfully"}


def _ensure_questions_are_editable(db: Session, assessment_id: int) -> None:
    attempt_id = db.scalar(
        select(AssessmentAttempt.id)
        .where(AssessmentAttempt.assessment_id == assessment_id)
        .limit(1)
    )
    if attempt_id is not None:
        raise HTTPException(
            status_code=409,
            detail="Assessment questions cannot change after an attempt is submitted",
        )


@router.get("/{assessment_id}/questions")
def get_assessment_questions(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assessment = db.get(AssessmentModel, assessment_id)
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
            raise HTTPException(status_code=403, detail="Enroll in this course to view questions")

    questions = db.scalars(
        select(AssessmentQuestion)
        .where(AssessmentQuestion.assessment_id == assessment_id)
        .order_by(AssessmentQuestion.position, AssessmentQuestion.id)
    )
    response_questions = []
    for question in questions:
        item = {
            "id": question.id,
            "assessment_id": question.assessment_id,
            "prompt": question.prompt,
            "options": question.options,
            "position": question.position,
        }
        if current_user.role == "admin":
            item["correct_option_index"] = question.correct_option_index
        response_questions.append(item)
    return {"assessment_id": assessment_id, "questions": response_questions}


@router.post("/{assessment_id}/questions", dependencies=[Depends(get_admin_user)])
def create_assessment_question(
    assessment_id: int,
    question: AssessmentQuestionCreate,
    db: Session = Depends(get_db),
):
    assessment = db.get(AssessmentModel, assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    _ensure_questions_are_editable(db, assessment_id)

    last_position = db.scalar(
        select(func.max(AssessmentQuestion.position)).where(
            AssessmentQuestion.assessment_id == assessment_id
        )
    ) or 0
    db_question = AssessmentQuestion(
        assessment_id=assessment_id,
        prompt=question.prompt,
        options=question.options,
        correct_option_index=question.correct_option_index,
        position=last_position + 1,
    )
    db.add(db_question)
    db.flush()
    assessment.total_questions = db.scalar(
        select(func.count(AssessmentQuestion.id)).where(
            AssessmentQuestion.assessment_id == assessment_id
        )
    ) or 0
    db.commit()
    db.refresh(db_question)
    return {
        "message": "Assessment question created successfully",
        "question": {
            "id": db_question.id,
            "assessment_id": db_question.assessment_id,
            "prompt": db_question.prompt,
            "options": db_question.options,
            "correct_option_index": db_question.correct_option_index,
            "position": db_question.position,
        },
    }


@router.patch(
    "/{assessment_id}/questions/{question_id}",
    dependencies=[Depends(get_admin_user)],
)
def update_assessment_question(
    assessment_id: int,
    question_id: int,
    question_update: AssessmentQuestionUpdate,
    db: Session = Depends(get_db),
):
    db_question = db.get(AssessmentQuestion, question_id)
    if db_question is None or db_question.assessment_id != assessment_id:
        raise HTTPException(status_code=404, detail="Assessment question not found")
    _ensure_questions_are_editable(db, assessment_id)

    updates = question_update.model_dump(exclude_unset=True, exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="At least one field must be provided")

    options = updates.get("options", db_question.options)
    correct_index = updates.get("correct_option_index", db_question.correct_option_index)
    if correct_index >= len(options):
        raise HTTPException(status_code=422, detail="correct_option_index must refer to an option")
    if any(not option.strip() for option in options):
        raise HTTPException(status_code=422, detail="Options cannot be blank")

    for field, value in updates.items():
        setattr(db_question, field, value)
    db.commit()
    db.refresh(db_question)
    return {
        "message": "Assessment question updated successfully",
        "question": {
            "id": db_question.id,
            "assessment_id": db_question.assessment_id,
            "prompt": db_question.prompt,
            "options": db_question.options,
            "correct_option_index": db_question.correct_option_index,
            "position": db_question.position,
        },
    }


@router.delete(
    "/{assessment_id}/questions/{question_id}",
    dependencies=[Depends(get_admin_user)],
)
def delete_assessment_question(
    assessment_id: int,
    question_id: int,
    db: Session = Depends(get_db),
):
    assessment = db.get(AssessmentModel, assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    db_question = db.get(AssessmentQuestion, question_id)
    if db_question is None or db_question.assessment_id != assessment_id:
        raise HTTPException(status_code=404, detail="Assessment question not found")
    _ensure_questions_are_editable(db, assessment_id)

    db.delete(db_question)
    db.flush()
    assessment.total_questions = db.scalar(
        select(func.count(AssessmentQuestion.id)).where(
            AssessmentQuestion.assessment_id == assessment_id
        )
    ) or 0
    db.commit()
    return {"message": "Assessment question deleted successfully"}