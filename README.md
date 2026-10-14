# VertexLearn AI
### AI-Powered Learning Management System

VertexLearn AI is an AI-powered Learning Management System (LMS)
that combines technical courses, structured lessons, assessments,
and an AI Study Assistant in a single platform.

The project aims to make technical learning more interactive by
allowing students to access learning materials, evaluate their
knowledge, and ask questions about course concepts.

---

## 1. Problem Statement

Students learning technical subjects often need to switch between
different platforms to access courses, practise questions, evaluate
their understanding, and clarify doubts.

Traditional course platforms may also require students to search
through learning materials or external resources when they do not
understand a particular concept.

This creates an opportunity to integrate course delivery,
assessments, and AI-assisted explanations into a single application.

## 2. Proposed Solution

VertexLearn AI provides a unified learning platform where students
can explore technical courses, access structured lessons, and
interact with an AI Study Assistant.

The application integrates a React frontend, a FastAPI backend,
a PostgreSQL database, and Google's Gemini API.

For AI-assisted learning, the backend attempts to identify
relevant lesson content using keyword matching and supplies that
content to Gemini along with the student's question.

Gemini generates an explanation that the application returns
to the student.

The objective is to help students understand course concepts
without leaving the learning platform.

---

## 3. Key Features

- **Course Exploration:** Browse available technical courses.
- **Structured Lessons:** Access course content organised into lessons.
- **Assessments:** Access available assessments to evaluate learning.
- **AI Study Assistant:** Ask questions about technical concepts.
- **Course-Context Retrieval:** Identify potentially relevant lesson
  content using keyword matching.
- **AI-Generated Explanations:** Use the Gemini API to generate
  responses using the student's question and retrieved context.

Note: Feature availability depends on the current implementation.
See the Future Improvements section for known limitations.

---

## 4. Technology Stack

### Frontend

| Technology | Purpose |
|---|---|
| React | Builds the interactive user interface. |
| Vite | Supports frontend development and builds. |
| JavaScript | Implements frontend interactions and application logic. |
| HTML | Defines page structure. |
| CSS | Styles the user interface. |

### Backend

| Technology | Purpose |
|---|---|
| Python | Implements backend and AI-related logic. |
| FastAPI | Provides backend API endpoints and request handling. |
| REST APIs | Enable communication between the frontend and backend. |
| Pydantic | Validates request data and structures responses where configured. |
| Uvicorn | Runs the FastAPI application. |

### Database

| Technology | Purpose |
|---|---|
| PostgreSQL | Stores application data. |
| SQLAlchemy | Supports database interaction from Python. |
| SQL | Used to query and manage relational data. |

### AI Integration

| Technology | Purpose |
|---|---|
| Google Gemini API | Generates AI-assisted explanations. |
| Python retrieval logic | Searches lesson titles and content using keyword matching. |
| Prompt engineering | Supplies instructions, the student's question, and course context to the AI model. |
| Retrieval-Augmented Generation (RAG) approach | Supplies retrieved course information as context for answer generation. |

The current retrieval approach uses keyword matching. Embedding-based
semantic search and vector database integration should not be
considered implemented unless they are added and verified.

---

## 5. System Architecture

The application separates the frontend, backend, database,
and AI integration into distinct components.

```text
                   STUDENT
                      |
                      v
              React + Vite
                 Frontend
                      |
                  HTTP / API
                      |
                      v
                FastAPI Backend
                 /           \
                v             v
        PostgreSQL         AI Service
        + SQLAlchemy           |
                               v
                     Keyword-Based Retrieval
                               |
                               v
                       Relevant Lesson Context
                               |
                               v
                         Gemini API
                               |
                               v
                       Generated Response
                               |
                               v
                        React Frontend
```

### Request Flow

1. The student interacts with the React frontend.
2. The frontend sends a request to a FastAPI endpoint.
3. The backend processes the request.
4. Database operations are performed when required.
5. For AI questions, the retrieval logic attempts to identify
   relevant lesson content.
6. The backend supplies the question and selected context to Gemini.
7. Gemini generates a response.
8. The backend returns the response to the frontend.

---

## 6. AI Study Assistant: How It Works

The AI Study Assistant is designed to help students clarify
concepts while studying.

For example, a student may ask:

"What is the difference between a Python list and a tuple?"

The workflow is:

1. **Question Input:** The student enters a question.
2. **Request Processing:** The frontend sends the question to the backend.
3. **Lesson Retrieval:** The backend searches available lesson text
   using keyword matching.
4. **Context Preparation:** Relevant lesson content is combined
   with the student's question.
5. **AI Generation:** The backend sends the prepared prompt to Gemini.
6. **Response Delivery:** The generated explanation is returned
   to the frontend.

This is a simple keyword-based retrieval-augmented generation
approach.

The application uses an existing AI model through its API rather
than training a new large language model.

---

## 7. Project Folder Structure

The project is stored locally at:

`~/VertexLearn-AI`

The local path is specific to the development machine. Other
developers should clone the repository and follow the setup
instructions below.

The main project structure is:

```text
VertexLearn-AI/
├── app/
│   ├── database/
│   ├── models/
│   ├── routers/
│   ├── schemas/
│   ├── services/
│   └── main.py
├── frontend/
│   ├── src/
│   ├── package.json
│   └── ...
├── tests/
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

This is a high-level overview. Individual files and folders may
vary according to the current implementation.

---

## 8. Installation and Local Setup

### Prerequisites

Install the following software:

- Python 3.11 or another version supported by the project dependencies.
- Node.js and npm.
- PostgreSQL.
- Git.

The versions listed above should be checked against the versions
used during development.

### Step 1: Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/VertexLearn-AI.git
cd VertexLearn-AI
```

Replace `YOUR_USERNAME` with the GitHub account that owns the repository.

### Step 2: Create a Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Backend Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Create a local `.env` file using `.env.example` as a reference.

Add the required configuration values, including the database
connection settings and Gemini API key.

Do not commit `.env` or expose real credentials.

Example configuration names may include:

```env
DATABASE_URL=
GEMINI_API_KEY=
AI_API_BASE_URL=
AI_MODEL=
```

Verify the actual variable names against the application's
configuration before running the project.

### Step 5: Configure PostgreSQL

Install and start PostgreSQL if it is not already running.

Create a database and configure the database connection according
to the application's environment settings.

Use the project's existing database models and setup instructions
to initialise the required tables.

### Step 6: Start the Backend

From the project root:

```bash
uvicorn app.main:app --reload
```

Backend URL:

http://127.0.0.1:8000

API documentation:

http://127.0.0.1:8000/docs

### Step 7: Install Frontend Dependencies

Open a second terminal:

```bash
cd frontend
npm install
```

### Step 8: Start the Frontend

```bash
npm run dev
```

Open the local URL displayed by Vite in the terminal.

The frontend API configuration must point to the running backend.

---

## 9. Challenges and Lessons Learned

This section should describe challenges that actually occurred
during development.

### AI Response Reliability

**Challenge:** AI-generated answers may occasionally be incomplete,
and external AI service errors can interrupt requests.

**Current approach:** The application integrates the Gemini API
and supplies the student's question with retrieved lesson context.

**Potential improvement:** Improve error handling, validate generated
responses, and evaluate answer completeness and relevance.

### Retrieving Relevant Course Content

**Challenge:** Keyword matching may fail to identify the best lesson
when a student uses different words from the lesson content.

**Current approach:** The retrieval logic matches terms in the
question against lesson titles and content.

**Potential improvement:** Evaluate embedding-based semantic search
to retrieve relevant lessons even when the wording differs.

### Configuration and Secret Management

**Challenge:** The application depends on environment-specific
configuration, including database credentials and AI API settings.

**Approach:** Keep secrets in environment variables and exclude
the local `.env` file from version control.

### Testing and Debugging

Document the actual errors you encountered, how you reproduced
them, what you changed, and how you verified the result.

Do not claim that a problem was solved unless you have tested
the corresponding functionality.

---

## 10. Current Limitations

- AI responses may occasionally be incomplete.
- External AI service failures may interrupt requests.
- Keyword-based retrieval may miss relevant lessons when the
  student's wording differs from the course content.
- Personalised recommendations and detailed learning analytics
  remain areas for future development.

The current feature set and limitations should be updated as
development progresses.

---

## 11. Future Improvements

- Improve AI response reliability and error handling.
- Evaluate embedding-based semantic retrieval.
- Improve relevance and quality of retrieved lesson content.
- Introduce personalised course recommendations.
- Add student performance analytics and learning progress reports.
- Expand automated tests for API and AI functionality.
- Improve security, configuration validation, and deployment.
- Deploy the application to a suitable hosting environment.

---

## 12. Security

- Never commit API keys, database passwords, JWT secrets,
  or other credentials.
- Keep `.env` excluded through `.gitignore`.
- Use `.env.example` with placeholder values.
- Rotate credentials if they have been exposed.
- Configure production secrets securely.
- Validate authentication and authorisation before deployment.

---

## 13. Project Status

**Status:** Under development.

VertexLearn AI provides a foundation for integrating technical
learning, assessments, and AI-assisted explanations.

Further work is needed to improve reliability, retrieval quality,
testing, and production readiness.

---

## 14. Author

**Developer:** S. Yashaswi

**GitHub:** https://github.com/Yash301201
