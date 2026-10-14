from app.database.connection import engine
from app.database.database import Base
from app.models import (
    assessment,
    assessment_answer,
    assessment_attempt,
    assessment_question,
    course,
    enrollment,
    lesson,
    lesson_completion,
    user,
)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")


if __name__ == "__main__":
    init_db()