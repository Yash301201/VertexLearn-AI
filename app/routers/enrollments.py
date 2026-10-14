from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.lesson import Lesson
from app.models.lesson_completion import LessonCompletion
from app.models.user import User
from app.routers.dependencies import get_admin_user, get_current_user
from app.schemas.enrollment import AdminEnrollmentResponse, EnrollmentResponse
from app.schemas.lesson import LessonCompletionResponse

router = APIRouter(
    prefix="/enrollments",
    tags=["Enrollments"],
)


def _progress_percent(db: Session, user_id: int, course_id: int) -> float:
    lesson_count = db.scalar(
        select(func.count(Lesson.id)).where(Lesson.course_id == course_id)
    ) or 0
    if lesson_count == 0:
        return 0.0

    completed_count = db.scalar(
        select(func.count(LessonCompletion.id))
        .join(Lesson, Lesson.id == LessonCompletion.lesson_id)
        .where(
            LessonCompletion.user_id == user_id,
            Lesson.course_id == course_id,
        )
    ) or 0
    return round(completed_count * 100 / lesson_count, 2)


@router.get("/", response_model=list[AdminEnrollmentResponse])
def get_all_enrollments(
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    rows = db.execute(
        select(Enrollment, User, Course)
        .join(User, User.id == Enrollment.user_id)
        .join(Course, Course.id == Enrollment.course_id)
        .order_by(Enrollment.id)
    ).all()
    return [
        {
            "id": enrollment.id,
            "course_id": course.id,
            "course_title": course.title,
            "enrolled_at": enrollment.enrolled_at,
            "progress_percent": _progress_percent(db, user.id, course.id),
            "user_id": user.id,
            "user_name": user.name,
            "user_email": user.email,
        }
        for enrollment, user, course in rows
    ]


@router.get("/me", response_model=list[EnrollmentResponse])
def get_my_enrollments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = db.execute(
        select(Enrollment, Course)
        .join(Course, Course.id == Enrollment.course_id)
        .where(Enrollment.user_id == current_user.id)
        .order_by(Enrollment.id)
    ).all()
    return [
        {
            "id": enrollment.id,
            "course_id": course.id,
            "course_title": course.title,
            "enrolled_at": enrollment.enrolled_at,
            "progress_percent": _progress_percent(db, current_user.id, course.id),
        }
        for enrollment, course in rows
    ]


@router.post("/courses/{course_id}", status_code=201)
def enroll_in_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if db.get(Course, course_id) is None:
        raise HTTPException(status_code=404, detail="Course not found")

    existing = db.scalar(
        select(Enrollment).where(
            Enrollment.user_id == current_user.id,
            Enrollment.course_id == course_id,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Already enrolled in this course")

    enrollment = Enrollment(user_id=current_user.id, course_id=course_id)
    db.add(enrollment)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Already enrolled in this course") from exc
    db.refresh(enrollment)
    return {
        "message": "Enrolled successfully",
        "enrollment": {
            "id": enrollment.id,
            "course_id": course_id,
            "enrolled_at": enrollment.enrolled_at,
            "progress_percent": 0.0,
        },
    }


@router.post(
    "/courses/{course_id}/lessons/{lesson_id}/complete",
    response_model=LessonCompletionResponse,
)
def complete_course_lesson(
    course_id: int,
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    enrolled = db.scalar(
        select(Enrollment.id).where(
            Enrollment.user_id == current_user.id,
            Enrollment.course_id == course_id,
        )
    )
    if enrolled is None:
        raise HTTPException(status_code=403, detail="Enroll in this course first")

    lesson = db.get(Lesson, lesson_id)
    if lesson is None or lesson.course_id != course_id:
        raise HTTPException(status_code=404, detail="Lesson not found in this course")

    completion = db.scalar(
        select(LessonCompletion).where(
            LessonCompletion.user_id == current_user.id,
            LessonCompletion.lesson_id == lesson_id,
        )
    )
    if completion is None:
        db.add(LessonCompletion(user_id=current_user.id, lesson_id=lesson_id))
        db.commit()

    return {
        "course_id": course_id,
        "lesson_id": lesson_id,
        "completed": True,
        "progress_percent": _progress_percent(db, current_user.id, course_id),
    }


@router.delete("/courses/{course_id}")
def withdraw_from_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    enrollment = db.scalar(
        select(Enrollment).where(
            Enrollment.user_id == current_user.id,
            Enrollment.course_id == course_id,
        )
    )
    if enrollment is None:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    lesson_ids = select(Lesson.id).where(Lesson.course_id == course_id)
    db.execute(
        delete(LessonCompletion).where(
            LessonCompletion.user_id == current_user.id,
            LessonCompletion.lesson_id.in_(lesson_ids),
        )
    )
    db.delete(enrollment)
    db.commit()
    return {"message": "Course enrollment withdrawn"}