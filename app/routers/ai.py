from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.student_success import build_student_success_agent
from app.database.connection import get_db
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.lesson import Lesson
from app.models.study_plan import StudyPlan, StudyPlanAudit
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


def _get_course_for_request(course_id: int, db: Session, current_user: User) -> Course:
	course = db.get(Course, course_id)
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
	return course


def _serialize_plan(plan: StudyPlan) -> dict:
	return {
		"id": plan.id,
		"status": plan.status,
		"rationale": plan.rationale,
		"tasks": plan.tasks,
		"reviewed_at": plan.reviewed_at.isoformat() if plan.reviewed_at else None,
	}


@router.post("/study")
def study_with_ai(
	request: AIStudyRequest,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
):
	course = _get_course_for_request(request.course_id, db, current_user)
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
			for lesson in context_lessons
		],
	}


@router.post("/agent")
def run_student_success_agent(
	request: AIStudyRequest,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
):
	_get_course_for_request(request.course_id, db, current_user)
	try:
		result = build_student_success_agent(db).invoke(
			{
				"question": request.question,
				"user_id": current_user.id,
				"course_id": request.course_id,
			}
		)
	except AIProviderNotConfigured as exc:
		raise HTTPException(
			status_code=503,
			detail="AI tutor is not configured. Set GEMINI_API_KEY and AI_MODEL, or configure a local OpenAI-compatible model endpoint.",
		) from exc
	except AIProviderError as exc:
		raise HTTPException(status_code=502, detail=str(exc)) from exc

	plan_payload = None
	progress = result.get("progress") or None
	tasks = result.get("plan_tasks", [])
	if result.get("intent") == "study_plan" and tasks:
		plan = StudyPlan(
			user_id=current_user.id,
			course_id=request.course_id,
			status="pending",
			rationale=result["answer"],
			tasks=tasks,
		)
		db.add(plan)
		db.flush()
		db.add(StudyPlanAudit(plan_id=plan.id, user_id=current_user.id, action="drafted"))
		db.commit()
		db.refresh(plan)
		plan_payload = _serialize_plan(plan)

	return {
		"intent": result.get("intent", "course_qa"),
		"answer": result.get("answer", ""),
		"sources": result.get("sources", []),
		"progress": progress,
		"plan": plan_payload,
	}


def _review_plan(plan_id: int, decision: str, db: Session, current_user: User) -> dict:
	plan = db.scalar(
		select(StudyPlan)
		.where(StudyPlan.id == plan_id, StudyPlan.user_id == current_user.id)
		.with_for_update()
	)
	if plan is None:
		raise HTTPException(status_code=404, detail="Study plan not found")

	if plan.status != "pending":
		if plan.status == decision:
			return _serialize_plan(plan)
		raise HTTPException(status_code=409, detail=f"Study plan was already {plan.status}")

	plan.status = decision
	plan.reviewed_at = datetime.now(timezone.utc)
	db.add(StudyPlanAudit(plan_id=plan.id, user_id=current_user.id, action=decision))
	db.commit()
	db.refresh(plan)
	return _serialize_plan(plan)


@router.post("/plans/{plan_id}/approve")
def approve_study_plan(
	plan_id: int,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
):
	return {"plan": _review_plan(plan_id, "approved", db, current_user)}


@router.post("/plans/{plan_id}/reject")
def reject_study_plan(
	plan_id: int,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
):
	return {"plan": _review_plan(plan_id, "rejected", db, current_user)}

