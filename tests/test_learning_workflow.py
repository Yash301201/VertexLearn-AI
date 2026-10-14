import os
import tempfile
import unittest
import uuid
from unittest.mock import patch

from sqlalchemy import func, select

from app.services.ai_service import retrieve_course_lessons


_test_directory = tempfile.TemporaryDirectory()
os.environ["DATABASE_URL"] = f"sqlite:///{_test_directory.name}/workflow.db"
os.environ["JWT_SECRET_KEY"] = "workflow-test-signing-secret-at-least-32-chars"
os.environ["ADMIN_EMAIL"] = "workflow-admin@example.com"
os.environ["ADMIN_PASSWORD"] = "workflow-admin-password"
os.environ["ADMIN_NAME"] = "Workflow Test Admin"

from fastapi.testclient import TestClient

from app.database.connection import SessionLocal, engine
from app.main import app
from app.models.assessment import Assessment
from app.models.assessment_question import AssessmentQuestion
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.lesson import Lesson
from app.models.user import User
from app.services.demo_seed import seed_demo_data


class LearningWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.__enter__()
        login = cls.client.post(
            "/auth/login",
            json={
                "email": os.environ["ADMIN_EMAIL"],
                "password": os.environ["ADMIN_PASSWORD"],
            },
        )
        if login.status_code != 200:
            raise AssertionError(login.text)
        cls.admin_headers = {
            "Authorization": f"Bearer {login.json()['access_token']}"
        }

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)
        engine.dispose()
        _test_directory.cleanup()

    def test_password_reset_link_can_only_be_used_once(self):
        suffix = uuid.uuid4().hex[:8]
        email = f"reset-{suffix}@example.com"
        old_password = "old-reset-password"
        new_password = "new-reset-password"
        registration = self.client.post(
            "/auth/register",
            json={"name": "Reset User", "email": email, "password": old_password},
        )
        self.assertEqual(registration.status_code, 200, registration.text)

        with patch("app.routers.auth.send_password_reset_email") as send_email:
            response = self.client.post("/auth/forgot-password", json={"email": email})
            self.assertEqual(response.status_code, 200, response.text)
            reset_token = send_email.call_args.args[1]

            unknown_response = self.client.post(
                "/auth/forgot-password", json={"email": f"missing-{suffix}@example.com"}
            )
            self.assertEqual(unknown_response.json(), response.json())
            send_email.assert_called_once()

        reset = self.client.post(
            "/auth/reset-password",
            json={"token": reset_token, "password": new_password},
        )
        self.assertEqual(reset.status_code, 200, reset.text)
        replay = self.client.post(
            "/auth/reset-password",
            json={"token": reset_token, "password": "another-reset-password"},
        )
        self.assertEqual(replay.status_code, 400)
        self.assertEqual(
            self.client.post(
                "/auth/login", json={"email": email, "password": old_password}
            ).status_code,
            401,
        )
        self.assertEqual(
            self.client.post(
                "/auth/login", json={"email": email, "password": new_password}
            ).status_code,
            200,
        )

    def test_z_ai_study_assistant_is_enrollment_scoped_and_returns_sources(self):
        seed_demo_data()
        courses = self.client.get("/courses/").json()["courses"]
        ai_course = next(
            course
            for course in courses
            if course["title"] == "Applied AI: Machine Learning to RAG Agents"
        )
        self.assertEqual(
            self.client.post(
                "/ai/study",
                json={"course_id": ai_course["id"], "question": "How does RAG retrieve sources?"},
            ).status_code,
            401,
        )

        fresh_login = self.client.post(
            "/auth/login",
            json={"email": "learner01@example.com", "password": "DemoLearner2026!"},
        )
        fresh_headers = {
            "Authorization": f"Bearer {fresh_login.json()['access_token']}"
        }
        self.assertEqual(
            self.client.post(
                "/ai/study",
                headers=fresh_headers,
                json={"course_id": ai_course["id"], "question": "How does RAG retrieve sources?"},
            ).status_code,
            403,
        )

        enrolled_login = self.client.post(
            "/auth/login",
            json={"email": "learner02@example.com", "password": "DemoLearner2026!"},
        )
        enrolled_headers = {
            "Authorization": f"Bearer {enrolled_login.json()['access_token']}"
        }
        with patch(
            "app.routers.ai.generate_grounded_answer",
            return_value="RAG retrieves relevant course passages before answering.",
        ):
            response = self.client.post(
                "/ai/study",
                headers=enrolled_headers,
                json={
                    "course_id": ai_course["id"],
                    "question": "How does RAG retrieve course sources?",
                },
            )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            response.json()["answer"],
            "RAG retrieves relevant course passages before answering.",
        )
        self.assertTrue(
            any("RAG" in source["title"] for source in response.json()["sources"])
        )

        with patch(
            "app.routers.ai.generate_grounded_answer",
            return_value="A supplemental explanation for this course topic.",
        ) as answer_generator:
            fallback_response = self.client.post(
                "/ai/study",
                headers=enrolled_headers,
                json={
                    "course_id": ai_course["id"],
                    "question": "Explain florpification in this course.",
                },
            )
        self.assertEqual(fallback_response.status_code, 200, fallback_response.text)
        self.assertEqual(fallback_response.json()["sources"], [])
        self.assertEqual(len(answer_generator.call_args.args[1]), 2)

    def test_seed_demo_data_is_repeatable(self):
        seed_demo_data()
        seed_demo_data()

        with SessionLocal() as db:
            learner_count = db.scalar(
                select(func.count()).select_from(User).where(
                    User.email.like("learner%@example.com")
                )
            )
            self.assertEqual(learner_count, 10)
            fresh_learner = db.scalar(
                select(User).where(User.email == "learner01@example.com")
            )
            self.assertEqual(
                db.scalar(
                    select(func.count()).select_from(Enrollment).where(
                        Enrollment.user_id == fresh_learner.id
                    )
                ),
                0,
            )
            python_course = db.scalar(
                select(Course).where(
                    Course.title == "Python Programming: Basics to DSA"
                )
            )
            mysql_course = db.scalar(
                select(Course).where(
                    Course.title == "MySQL: Beginner to Practical SQL"
                )
            )
            applied_ai_course = db.scalar(
                select(Course).where(
                    Course.title == "Applied AI: Machine Learning to RAG Agents"
                )
            )
            self.assertIsNotNone(python_course)
            self.assertIsNotNone(mysql_course)
            self.assertIsNotNone(applied_ai_course)
            condition_lessons = retrieve_course_lessons(
                "What is an if statement in Python? Give a simple example that checks whether a number is positive or negative, and explain the code line by line.",
                list(
                    db.scalars(
                        select(Lesson)
                        .where(Lesson.course_id == python_course.id)
                        .order_by(Lesson.position)
                    )
                ),
            )
            self.assertEqual(condition_lessons[0].title, "Conditions and loops")
            self.assertEqual(len(condition_lessons), 1)
            python_lesson_count = db.scalar(
                select(func.count()).select_from(Lesson).where(
                    Lesson.course_id == python_course.id
                )
            )
            mysql_lesson_count = db.scalar(
                select(func.count()).select_from(Lesson).where(
                    Lesson.course_id == mysql_course.id
                )
            )
            ai_lesson_count = db.scalar(
                select(func.count()).select_from(Lesson).where(
                    Lesson.course_id == applied_ai_course.id
                )
            )
            self.assertEqual(python_lesson_count, 16)
            self.assertEqual(mysql_lesson_count, 12)
            self.assertEqual(ai_lesson_count, 15)
            for course, expected_lessons in (
                (python_course, 16),
                (mysql_course, 12),
                (applied_ai_course, 15),
            ):
                detailed_count = db.scalar(
                    select(func.count()).select_from(Lesson).where(
                        Lesson.course_id == course.id,
                        Lesson.content.contains("Concepts and walkthrough:"),
                    )
                )
                self.assertEqual(detailed_count, expected_lessons)
            python_lists_lesson = db.scalar(
                select(Lesson).where(
                    Lesson.course_id == python_course.id,
                    Lesson.title == "Lists, tuples, and dictionaries",
                )
            )
            self.assertIn("Syntax and example:", python_lists_lesson.content)
            self.assertIn("ordered, mutable sequence", python_lists_lesson.content)
            self.assertIn("scores = [82, 91, 76]", python_lists_lesson.content)
            self.assertIn("scores.pop(1)", python_lists_lesson.content)
            self.assertTrue(
                {python_course.id, mysql_course.id, applied_ai_course.id}.issubset(
                    set(db.scalars(select(Assessment.course_id)))
                )
            )
            demo_assessments = list(
                db.scalars(
                    select(Assessment).where(
                        Assessment.title.in_(
                            [
                                "Python Basics Assessment",
                                "Python Foundations Assignment",
                                "Python Data Structures and Algorithms Assignment",
                                "MySQL Fundamentals Assignment",
                                "MySQL Joins and Data Design Assignment",
                                "Applied AI: ML and Evaluation Assignment",
                                "Applied AI: LLMs and Prompt Design Assignment",
                                "Applied AI: RAG, Agents, and Responsible Use Assignment",
                            ]
                        )
                    )
                )
            )
            self.assertEqual(len(demo_assessments), 8)
            for demo_assessment in demo_assessments:
                question_count = db.scalar(
                    select(func.count()).select_from(AssessmentQuestion).where(
                        AssessmentQuestion.assessment_id == demo_assessment.id
                    )
                )
                expected_question_count = (
                    20 if demo_assessment.title == "Python Basics Assessment" else 4
                )
                self.assertEqual(question_count, expected_question_count)

        assessment_catalog = self.client.get("/assessments/").json()["assessments"]
        self.assertTrue(all(assessment["ready"] for assessment in assessment_catalog))
        python_basics = next(
            assessment
            for assessment in assessment_catalog
            if assessment["title"] == "Python Basics Assessment"
        )
        self.assertEqual(python_basics["question_count"], 20)

    def test_enrollment_lessons_assessment_and_permissions(self):
        suffix = uuid.uuid4().hex[:8]
        course_response = self.client.post(
            "/courses/",
            headers=self.admin_headers,
            json={
                "title": f"Workflow Course {suffix}",
                "description": "Course used by the learning workflow test.",
                "instructor": "Workflow Test",
            },
        )
        self.assertEqual(course_response.status_code, 200, course_response.text)
        course_id = course_response.json()["course"]["id"]
        course_update = self.client.patch(
            f"/courses/{course_id}",
            headers=self.admin_headers,
            json={"instructor": "Updated Workflow Instructor"},
        )
        self.assertEqual(course_update.status_code, 200, course_update.text)
        self.assertEqual(
            course_update.json()["course"]["instructor"],
            "Updated Workflow Instructor",
        )

        lesson_responses = [
            self.client.post(
                f"/courses/{course_id}/lessons",
                headers=self.admin_headers,
                json={"title": "First Lesson", "content": "First lesson content."},
            ),
            self.client.post(
                f"/courses/{course_id}/lessons",
                headers=self.admin_headers,
                json={"title": "Second Lesson", "content": "Second lesson content."},
            ),
        ]
        for response in lesson_responses:
            self.assertEqual(response.status_code, 200, response.text)
        first_lesson_id = lesson_responses[0].json()["lesson"]["id"]
        second_lesson_id = lesson_responses[1].json()["lesson"]["id"]
        lesson_update = self.client.patch(
            f"/courses/{course_id}/lessons/{first_lesson_id}",
            headers=self.admin_headers,
            json={"title": "Updated First Lesson"},
        )
        self.assertEqual(lesson_update.status_code, 200, lesson_update.text)
        temporary_lesson = self.client.post(
            f"/courses/{course_id}/lessons",
            headers=self.admin_headers,
            json={"title": "Temporary Lesson", "content": "This lesson will be deleted."},
        )
        self.assertEqual(temporary_lesson.status_code, 200, temporary_lesson.text)
        temporary_lesson_id = temporary_lesson.json()["lesson"]["id"]
        lesson_delete = self.client.delete(
            f"/courses/{course_id}/lessons/{temporary_lesson_id}",
            headers=self.admin_headers,
        )
        self.assertEqual(lesson_delete.status_code, 200, lesson_delete.text)

        email = f"workflow-user-{suffix}@example.com"
        password = "workflow-user-password"
        registration = self.client.post(
            "/auth/register",
            json={"name": "Workflow User", "email": email, "password": password},
        )
        self.assertEqual(registration.status_code, 200, registration.text)
        user_id = registration.json()["student"]["id"]
        self.assertEqual(registration.json()["student"]["role"], "user")
        user_login = self.client.post(
            "/auth/login", json={"email": email, "password": password}
        )
        self.assertEqual(user_login.status_code, 200, user_login.text)
        user_headers = {
            "Authorization": f"Bearer {user_login.json()['access_token']}"
        }
        current_user = self.client.get("/auth/me", headers=user_headers)
        self.assertEqual(current_user.status_code, 200, current_user.text)
        self.assertEqual(
            current_user.json(),
            {
                "id": user_id,
                "name": "Workflow User",
                "email": email,
                "role": "user",
            },
        )
        self.assertEqual(self.client.get("/auth/me").status_code, 401)

        self.assertEqual(
            self.client.get(
                f"/courses/{course_id}/lessons", headers=user_headers
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                f"/courses/{course_id}/lessons",
                headers=user_headers,
                json={"title": "Forbidden Lesson", "content": "Not allowed."},
            ).status_code,
            403,
        )
        enrollment = self.client.post(
            f"/enrollments/courses/{course_id}", headers=user_headers
        )
        self.assertEqual(enrollment.status_code, 201, enrollment.text)
        self.assertEqual(
            self.client.post(
                f"/enrollments/courses/{course_id}", headers=user_headers
            ).status_code,
            409,
        )
        lessons = self.client.get(
            f"/courses/{course_id}/lessons", headers=user_headers
        )
        self.assertEqual(lessons.status_code, 200, lessons.text)
        self.assertEqual(len(lessons.json()["lessons"]), 2)
        self.assertTrue(all(not lesson["completed"] for lesson in lessons.json()["lessons"]))

        completion = self.client.post(
            f"/enrollments/courses/{course_id}/lessons/{first_lesson_id}/complete",
            headers=user_headers,
        )
        self.assertEqual(completion.status_code, 200, completion.text)
        self.assertEqual(completion.json()["progress_percent"], 50.0)
        lesson_statuses = self.client.get(
            f"/courses/{course_id}/lessons", headers=user_headers
        ).json()["lessons"]
        self.assertTrue(lesson_statuses[0]["completed"])
        self.assertFalse(lesson_statuses[1]["completed"])
        self.assertEqual(
            self.client.get("/enrollments/me", headers=user_headers)
            .json()[0]["progress_percent"],
            50.0,
        )

        assessment_response = self.client.post(
            "/assessments/",
            headers=self.admin_headers,
            json={
                "title": f"Workflow Quiz {suffix}",
                "course_id": course_id,
                "total_questions": 1,
                "passing_score": 50,
            },
        )
        self.assertEqual(assessment_response.status_code, 200, assessment_response.text)
        assessment_id = assessment_response.json()["assessment"]["id"]
        assessment_update = self.client.patch(
            f"/assessments/{assessment_id}",
            headers=self.admin_headers,
            json={"title": f"Updated Workflow Quiz {suffix}"},
        )
        self.assertEqual(assessment_update.status_code, 200, assessment_update.text)
        question_responses = [
            self.client.post(
                f"/assessments/{assessment_id}/questions",
                headers=self.admin_headers,
                json={
                    "prompt": "Which option is correct for question one?",
                    "options": ["Incorrect", "Correct"],
                    "correct_option_index": 1,
                },
            ),
            self.client.post(
                f"/assessments/{assessment_id}/questions",
                headers=self.admin_headers,
                json={
                    "prompt": "Which option is correct for question two?",
                    "options": ["Correct", "Incorrect"],
                    "correct_option_index": 0,
                },
            ),
        ]
        for response in question_responses:
            self.assertEqual(response.status_code, 200, response.text)
        question_ids = [response.json()["question"]["id"] for response in question_responses]
        temporary_question = self.client.post(
            f"/assessments/{assessment_id}/questions",
            headers=self.admin_headers,
            json={
                "prompt": "This temporary question will be removed.",
                "options": ["Option A", "Option B"],
                "correct_option_index": 0,
            },
        )
        self.assertEqual(temporary_question.status_code, 200, temporary_question.text)
        question_delete = self.client.delete(
            f"/assessments/{assessment_id}/questions/{temporary_question.json()['question']['id']}",
            headers=self.admin_headers,
        )
        self.assertEqual(question_delete.status_code, 200, question_delete.text)
        assessment_detail = self.client.get(f"/assessments/{assessment_id}")
        self.assertEqual(assessment_detail.json()["assessment"]["total_questions"], 2)

        learner_questions = self.client.get(
            f"/assessments/{assessment_id}/questions", headers=user_headers
        )
        self.assertEqual(learner_questions.status_code, 200, learner_questions.text)
        self.assertNotIn(
            "correct_option_index", learner_questions.json()["questions"][0]
        )
        self.assertEqual(
            self.client.get("/enrollments/", headers=user_headers).status_code,
            403,
        )

        attempt = self.client.post(
            f"/attempts/assessments/{assessment_id}",
            headers=user_headers,
            json={
                "answers": [
                    {"question_id": question_ids[0], "selected_option_index": 1},
                    {"question_id": question_ids[1], "selected_option_index": 1},
                ]
            },
        )
        self.assertEqual(attempt.status_code, 201, attempt.text)
        self.assertEqual(attempt.json()["score"], 50.0)
        self.assertTrue(attempt.json()["passed"])
        attempt_id = attempt.json()["id"]
        self.assertEqual(
            self.client.get("/attempts/me", headers=user_headers).status_code,
            200,
        )
        self.assertEqual(
            self.client.get("/attempts/", headers=user_headers).status_code,
            403,
        )
        self.assertEqual(
            self.client.patch(
                f"/assessments/{assessment_id}/questions/{question_ids[0]}",
                headers=self.admin_headers,
                json={"prompt": "Changing a question after submission is blocked."},
            ).status_code,
            409,
        )
        self.assertEqual(
            self.client.get("/attempts/{0}".format(attempt_id), headers=user_headers)
            .json()["user_id"],
            user_id,
        )

        admin_enrollments = self.client.get("/enrollments/", headers=self.admin_headers)
        self.assertEqual(admin_enrollments.status_code, 200, admin_enrollments.text)
        self.assertEqual(admin_enrollments.json()[0]["progress_percent"], 50.0)

        deleted = self.client.delete(
            f"/courses/{course_id}", headers=self.admin_headers
        )
        self.assertEqual(deleted.status_code, 200, deleted.text)
        self.assertEqual(
            self.client.get(f"/courses/{course_id}").status_code,
            404,
        )
        self.assertEqual(
            self.client.get(f"/attempts/{attempt_id}", headers=user_headers).status_code,
            404,
        )
        self.assertEqual(
            self.client.get("/enrollments/me", headers=user_headers).json(),
            [],
        )


if __name__ == "__main__":
    unittest.main()