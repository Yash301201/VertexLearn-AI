from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import inspect, text

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
    study_plan,
    user,
)

from app.routers import auth
from app.routers import courses
from app.routers import assessments
from app.routers import users
from app.routers import enrollments
from app.routers import attempts
from app.routers import ai
from app.services.admin_bootstrap import bootstrap_admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Importing the models above registers their tables with Base.metadata.
    Base.metadata.create_all(bind=engine)
    user_columns = {column["name"] for column in inspect(engine).get_columns("users")}
    if "role" not in user_columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user'")
            )
    bootstrap_admin()
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    yield
    engine.dispose()


app = FastAPI(
    title="VertexLearn AI",
    description="An Intelligent and Personalized Learning Management System",
    version="1.0.0",
    lifespan=lifespan,
)


app.include_router(auth.router)
app.include_router(courses.router)
app.include_router(assessments.router)
app.include_router(users.router)
app.include_router(enrollments.router)
app.include_router(attempts.router)
app.include_router(ai.router)


@app.get("/")
def home():
    return {
        "message": "Welcome to VertexLearn AI"
    }


@app.get("/about")
def about():
    return {
        "project": "VertexLearn AI",
        "description": "AI-powered Learning Management System"
    }
