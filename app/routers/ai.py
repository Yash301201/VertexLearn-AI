from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.lesson import Lesson
from app.models.user import User
from app.routers.dependencies import get_current_user
from app.schemas.ai import AIStudyRequest
from app.services.ai_service import (
	AIProviderError,
	AIProviderNotConfigured,
	generate_grounded_answer,
	retrieve_course_lessons,
)

router = APIRouter(prefix="/ai", tags=["AI Study Assistant"])


@router.post("/study")
def study_with_ai(
	request: AIStudyRequest,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
):
	course = db.get(Course, request.course_id)
	if course is None:
		raise HTTPException(status_code=404, detail="Course not found")

	if current_user.role != "admin":
		enrollment = db.scalar(
			select(Enrollment.id).where(
				Enrollment.user_id == current_user.id,
				Enrollment.course_id == course.id,
			)
		)
		if enrollment is None:
			raise HTTPException(status_code=403, detail="Enroll in this course to use its study assistant")

	lessons = list(
		db.scalars(
			select(Lesson)
			.where(Lesson.course_id == course.id)
			.order_by(Lesson.position, Lesson.id)
		)
	)
	retrieved_lessons = retrieve_course_lessons(request.question, lessons)
	if not lessons:
		return {
			"answer": "I could not find a relevant lesson in this course for that question. Try using the course topic or lesson title in your question.",
			"sources": [],
		}

	context_lessons = retrieved_lessons or lessons[:2]
	try:
		answer = generate_grounded_answer(request.question, context_lessons)
	except AIProviderNotConfigured as exc:
		raise HTTPException(
			status_code=503,
			detail="AI tutor is not configured. Set GEMINI_API_KEY and AI_MODEL, or configure a local OpenAI-compatible model endpoint.",
		) from exc
	except AIProviderError as exc:
		raise HTTPException(status_code=502, detail=str(exc)) from exc

	return {
		"answer": answer,
		"sources": [
			{"lesson_id": lesson.id, "title": lesson.title}
			for lesson in retrieved_lessons
		],
	}