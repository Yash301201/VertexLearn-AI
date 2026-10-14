from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base

if TYPE_CHECKING:
    from app.models.assessment_attempt import AssessmentAttempt
    from app.models.assessment_question import AssessmentQuestion
    from app.models.course import Course


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )

    course_id: Mapped[int] = mapped_column(
        ForeignKey(
            "courses.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    total_questions: Mapped[int] = mapped_column(
        nullable=False
    )

    passing_score: Mapped[float] = mapped_column(
        nullable=False
    )

    course: Mapped["Course"] = relationship(back_populates="assessments")
    questions: Mapped[list["AssessmentQuestion"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )
    attempts: Mapped[list["AssessmentAttempt"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )