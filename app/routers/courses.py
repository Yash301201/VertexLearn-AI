import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.course import Course as CourseModel
from app.models.enrollment import Enrollment
from app.models.lesson import Lesson
from app.models.lesson_completion import LessonCompletion
from app.models.user import User
from app.routers.dependencies import get_admin_user, get_current_user
from app.schemas.course import CourseCreate, CourseUpdate
from app.schemas.lesson import LessonCreate, LessonUpdate

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/courses",
    tags=["Courses"]
)


@router.get("/")
def get_courses(db: Session = Depends(get_db)):
    logger.info("Fetching all courses")
    return {
        "message": "Courses API is working",
        "courses": [
            {
                "id": course.id,
                "title": course.title,
                "description": course.description,
                "instructor": course.instructor,
            }
            for course in db.scalars(select(CourseModel).order_by(CourseModel.id))
        ],
    }


@router.get("/{course_id}")
def get_course(course_id: int, db: Session = Depends(get_db)):
    logger.info("Fetching course with id=%s", course_id)
    course = db.get(CourseModel, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return {
        "message": "Course details",
        "course": {
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "instructor": course.instructor,
        },
    }


@router.post("/", dependencies=[Depends(get_admin_user)])
def create_course(course: CourseCreate, db: Session = Depends(get_db)):
    logger.info("Creating course title=%s instructor=%s", course.title, course.instructor)
    db_course = CourseModel(**course.model_dump())
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return {
        "message": "Course created successfully",
        "course": {
            "id": db_course.id,
            "title": db_course.title,
            "description": db_course.description,
            "instructor": db_course.instructor,
        },
    }


@router.patch("/{course_id}", dependencies=[Depends(get_admin_user)])
def update_course(
    course_id: int,
    course_update: CourseUpdate,
    db: Session = Depends(get_db),
):
    db_course = db.get(CourseModel, course_id)
    if db_course is None:
        raise HTTPException(status_code=404, detail="Course not found")

    updates = course_update.model_dump(exclude_unset=True, exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="At least one field must be provided")

    for field, value in updates.items():
        setattr(db_course, field, value)

    db.commit()
    db.refresh(db_course)
    return {
        "message": "Course updated successfully",
        "course": {
            "id": db_course.id,
            "title": db_course.title,
            "description": db_course.description,
            "instructor": db_course.instructor,
        },
    }


@router.delete("/{course_id}", dependencies=[Depends(get_admin_user)])
def delete_course(course_id: int, db: Session = Depends(get_db)):
    db_course = db.get(CourseModel, course_id)
    if db_course is None:
        raise HTTPException(status_code=404, detail="Course not found")

    db.delete(db_course)
    db.commit()
    return {"message": "Course and its learning data deleted successfully"}


@router.get("/{course_id}/lessons")
def get_course_lessons(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    course = db.get(CourseModel, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    enrollment = db.scalar(
        select(Enrollment.id).where(
            Enrollment.course_id == course_id,
            Enrollment.user_id == current_user.id,
        )
    )
    if current_user.role != "admin" and enrollment is None:
        raise HTTPException(status_code=403, detail="Enroll in this course to view its lessons")

    lessons = list(db.scalars(
        select(Lesson)
        .where(Lesson.course_id == course_id)
        .order_by(Lesson.position, Lesson.id)
    ))
    completed_lesson_ids = (
        set(
            db.scalars(
                select(LessonCompletion.lesson_id).where(
                    LessonCompletion.user_id == current_user.id,
                    LessonCompletion.lesson_id.in_([lesson.id for lesson in lessons]),
                )
            )
        )
        if lessons
        else set()
    )
    return {
        "course_id": course_id,
        "lessons": [
            {
                "id": lesson.id,
                "title": lesson.title,
                "content": lesson.content,
                "position": lesson.position,
                "completed": lesson.id in completed_lesson_ids,
            }
            for lesson in lessons
        ],
    }


@router.post("/{course_id}/lessons", dependencies=[Depends(get_admin_user)])
def create_course_lesson(
    course_id: int,
    lesson: LessonCreate,
    db: Session = Depends(get_db),
):
    if db.get(CourseModel, course_id) is None:
        raise HTTPException(status_code=404, detail="Course not found")

    last_position = db.scalar(
        select(func.max(Lesson.position)).where(Lesson.course_id == course_id)
    ) or 0
    db_lesson = Lesson(
        course_id=course_id,
        title=lesson.title,
        content=lesson.content,
        position=last_position + 1,
    )
    db.add(db_lesson)
    db.commit()
    db.refresh(db_lesson)
    return {
        "message": "Lesson created successfully",
        "lesson": {
            "id": db_lesson.id,
            "course_id": db_lesson.course_id,
            "title": db_lesson.title,
            "content": db_lesson.content,
            "position": db_lesson.position,
        },
    }


@router.patch(
    "/{course_id}/lessons/{lesson_id}",
    dependencies=[Depends(get_admin_user)],
)
def update_course_lesson(
    course_id: int,
    lesson_id: int,
    lesson_update: LessonUpdate,
    db: Session = Depends(get_db),
):
    db_lesson = db.get(Lesson, lesson_id)
    if db_lesson is None or db_lesson.course_id != course_id:
        raise HTTPException(status_code=404, detail="Lesson not found")

    updates = lesson_update.model_dump(exclude_unset=True, exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="At least one field must be provided")
    for field, value in updates.items():
        setattr(db_lesson, field, value)

    db.commit()
    db.refresh(db_lesson)
    return {
        "message": "Lesson updated successfully",
        "lesson": {
            "id": db_lesson.id,
            "course_id": db_lesson.course_id,
            "title": db_lesson.title,
            "content": db_lesson.content,
            "position": db_lesson.position,
        },
    }


@router.delete(
    "/{course_id}/lessons/{lesson_id}",
    dependencies=[Depends(get_admin_user)],
)
def delete_course_lesson(
    course_id: int,
    lesson_id: int,
    db: Session = Depends(get_db),
):
    db_lesson = db.get(Lesson, lesson_id)
    if db_lesson is None or db_lesson.course_id != course_id:
        raise HTTPException(status_code=404, detail="Lesson not found")

    db.delete(db_lesson)
    db.commit()
    return {"message": "Lesson and its completion records deleted successfully"}