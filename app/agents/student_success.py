"""A bounded LangGraph workflow built on VertexLearn's existing learner data."""

from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.lesson import Lesson
from app.services.ai_service import generate_grounded_answer, retrieve_course_lessons


PROGRESS_SQL = """
WITH enrolled_lessons AS (
    SELECT c.id AS course_id,
           c.title AS course_title,
           l.id AS lesson_id,
           l.title AS lesson_title,
           l.position,
           lc.id AS completion_id
    FROM enrollments e
    JOIN courses c ON c.id = e.course_id
    JOIN lessons l ON l.course_id = c.id
    LEFT JOIN lesson_completions lc
      ON lc.lesson_id = l.id AND lc.user_id = e.user_id
    WHERE e.user_id = :user_id
      AND e.course_id = :course_id
), course_summary AS (
    SELECT course_id,
           course_title,
           COUNT(lesson_id)::int AS total_lessons,
           COUNT(completion_id)::int AS completed_lessons
    FROM enrolled_lessons
    GROUP BY course_id, course_title
), next_lessons AS (
    SELECT course_id,
           lesson_id,
           lesson_title,
           position,
           ROW_NUMBER() OVER (
               PARTITION BY course_id ORDER BY position, lesson_id
           ) AS next_rank
    FROM enrolled_lessons
    WHERE completion_id IS NULL
)
SELECT s.course_id,
       s.course_title,
       s.total_lessons,
       s.completed_lessons,
       CASE WHEN s.total_lessons = 0 THEN 0
            ELSE ROUND(100.0 * s.completed_lessons / s.total_lessons)::int END AS completion_percent,
       n.lesson_id AS next_lesson_id,
       n.lesson_title AS next_lesson_title,
       n.position AS next_lesson_position
FROM course_summary s
LEFT JOIN next_lessons n
  ON n.course_id = s.course_id AND n.next_rank <= 3
ORDER BY n.next_rank
"""

PLAN_TERMS = (
    "study plan",
    "what should i study",
    "what to study",
    "what next",
    "study next",
    "next lesson",
    "recommend",
    "plan my",
    "revision plan",
)


class AgentState(TypedDict, total=False):
    question: str
    user_id: int
    course_id: int
    intent: Literal["course_qa", "study_plan"]
    context_lessons: list[Lesson]
    sources: list[dict]
    progress: dict
    plan_tasks: list[dict]
    answer: str


def get_course_progress(db: Session, user_id: int, course_id: int) -> dict | None:
    rows = db.execute(
        text(PROGRESS_SQL),
        {"user_id": user_id, "course_id": course_id},
    ).mappings().all()
    if not rows:
        return None

    first = rows[0]
    return {
        "course_id": first["course_id"],
        "course_title": first["course_title"],
        "total_lessons": first["total_lessons"],
        "completed_lessons": first["completed_lessons"],
        "completion_percent": first["completion_percent"],
        "next_lessons": [
            {
                "lesson_id": row["next_lesson_id"],
                "title": row["next_lesson_title"],
                "position": row["next_lesson_position"],
                "estimated_minutes": 15,
            }
            for row in rows
            if row["next_lesson_id"] is not None
        ],
    }


def build_student_success_agent(db: Session):
    """Build a request-scoped graph; model output cannot issue arbitrary SQL."""

    def classify(state: AgentState) -> AgentState:
        question = state["question"].casefold()
        intent = "study_plan" if any(term in question for term in PLAN_TERMS) else "course_qa"
        return {"intent": intent}

    def retrieve_lessons(state: AgentState) -> AgentState:
        lessons = list(
            db.query(Lesson)
            .filter(Lesson.course_id == state["course_id"])
            .order_by(Lesson.position, Lesson.id)
            .all()
        )
        retrieved = retrieve_course_lessons(state["question"], lessons)
        context_lessons = retrieved or lessons[:2]
        return {
            "context_lessons": context_lessons,
            "sources": [
                {"lesson_id": lesson.id, "title": lesson.title}
                for lesson in context_lessons
            ],
        }

    def load_progress(state: AgentState) -> AgentState:
        progress = get_course_progress(db, state["user_id"], state["course_id"])
        tasks = [
            {
                "lesson_id": lesson["lesson_id"],
                "title": lesson["title"],
                "description": "Continue with this course lesson, then review its key ideas.",
                "estimated_minutes": lesson["estimated_minutes"],
            }
            for lesson in (progress or {}).get("next_lessons", [])
        ]
        return {"progress": progress or {}, "plan_tasks": tasks}

    def compose_answer(state: AgentState) -> AgentState:
        if state["intent"] == "course_qa":
            if not state.get("context_lessons"):
                return {
                    "answer": "This course does not have any lessons available to answer from yet."
                }
            answer = generate_grounded_answer(
                state["question"],
                state.get("context_lessons", []),
            )
            return {"answer": answer}

        progress = state.get("progress", {})
        tasks = state.get("plan_tasks", [])
        if not progress:
            return {
                "answer": "I couldn't find an enrollment or progress record for this course. Enroll in the course to generate a personalized study plan."
            }
        if not tasks:
            return {
                "answer": f"You've completed all {progress['total_lessons']} lessons in {progress['course_title']}. Choose another course to plan your next session."
            }
        return {
            "answer": (
                f"You've completed {progress['completed_lessons']} of {progress['total_lessons']} lessons "
                f"in {progress['course_title']} ({progress['completion_percent']}%). "
                "I drafted the next lessons below. Review the draft and approve it to save your plan."
            )
        }

    graph = StateGraph(AgentState)
    graph.add_node("classify", classify)
    graph.add_node("retrieve_lessons", retrieve_lessons)
    graph.add_node("load_progress", load_progress)
    graph.add_node("compose_answer", compose_answer)
    graph.add_edge(START, "classify")
    graph.add_conditional_edges(
        "classify",
        lambda state: state["intent"],
        {"course_qa": "retrieve_lessons", "study_plan": "load_progress"},
    )
    graph.add_edge("retrieve_lessons", "compose_answer")
    graph.add_edge("load_progress", "compose_answer")
    graph.add_edge("compose_answer", END)
    return graph.compile()

