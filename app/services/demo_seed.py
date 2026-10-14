import os

from sqlalchemy import delete, select

from app.database.connection import SessionLocal, engine
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
from app.models.course import Course
from app.models.assessment import Assessment
from app.models.assessment_question import AssessmentQuestion
from app.models.enrollment import Enrollment
from app.models.lesson import Lesson
from app.models.lesson_completion import LessonCompletion
from app.models.user import User
from app.services.admin_bootstrap import bootstrap_admin
from app.services.auth_service import hash_password


_LEARNERS = (
    "Avery Morgan",
    "Jordan Lee",
    "Sam Taylor",
    "Riley Patel",
    "Casey Kim",
    "Alex Rivera",
    "Jamie Chen",
    "Cameron Singh",
    "Drew Wilson",
    "Quinn Brooks",
)

_COURSES = (
    {
        "title": "Python Programming: Basics to DSA",
        "description": (
            "Build a strong Python foundation, then apply it to data structures, "
            "algorithms, complexity analysis, and a practical capstone."
        ),
        "lessons": (
            ("Getting started with Python", "Set up Python and run your first script. Learn how the interpreter executes a file, how to use the REPL, and how to read a basic traceback. Practice printing values and adding clear comments."),
            ("Variables, types, and expressions", "Work with integers, floats, strings, and booleans. Use type conversion and arithmetic operators, and learn why naming and predictable types make programs easier to understand."),
            ("Strings and input", "Collect user input and transform text with indexing, slicing, and useful string methods. Format output with f-strings and build a small command-line profile prompt."),
            ("Conditions and loops", "Make decisions with if, elif, and else, then repeat work with for and while loops. Practice ranges, loop control, and tracing the state of a program."),
            ("Functions and modules", "Write reusable functions with parameters and return values. Explore scope, default arguments, imports, and splitting a small program into modules."),
            ("Lists, tuples, and dictionaries", "Choose the right collection for ordered data, fixed groups, and key-value lookup. Practice iteration, common methods, membership checks, and nested structures."),
            ("Sets, comprehensions, and exceptions", "Use sets for uniqueness, comprehensions for concise transformations, and exceptions for expected failures. Build input validation that reports useful errors instead of crashing."),
            ("Files and useful standard-library tools", "Read and write text files safely with context managers. Explore pathlib, json, and collections to solve everyday data-processing tasks."),
            ("Classes and object-oriented Python", "Model related state and behavior with classes, instances, and methods. Introduce constructors, properties, composition, and when a simple function is the clearer choice."),
            ("Recursion and problem solving", "Break a problem into a smaller instance of itself and define a base case. Trace recursive calls, avoid missing base cases, and compare a recursive solution with an iterative one."),
            ("Algorithm analysis and Big O", "Estimate how time and memory grow as input grows. Compare constant, logarithmic, linear, and quadratic work using loops and simple measurements."),
            ("Arrays, stacks, and queues", "Use Python lists as dynamic arrays, then implement stack and queue behavior. Apply these structures to balanced delimiters, undo history, and breadth-first processing."),
            ("Linked lists and hash tables", "Understand node-based lists and the trade-off between traversal and insertion. Use dictionaries and sets as practical hash tables, and reason about collisions and average lookup cost."),
            ("Searching and sorting", "Implement linear and binary search, then compare insertion sort, merge sort, and Python's built-in sorting. Check preconditions and evaluate performance on different input sizes."),
            ("Trees and graph traversal", "Represent trees and graphs, then traverse them with depth-first and breadth-first search. Practice binary search trees, adjacency lists, visited sets, and shortest unweighted paths."),
            ("Dynamic programming and DSA capstone", "Recognize overlapping subproblems and use memoization or tabulation. Finish by choosing suitable data structures, analyzing complexity, and testing a small end-to-end problem-solving project."),
        ),
        "explanations": (
            "Python runs statements from top to bottom. The interpreter reports syntax errors before or during execution, and tracebacks identify where a runtime failure occurred. The interactive REPL is useful for trying one expression; scripts are better for saved programs. Indentation is part of Python syntax, so use consistent four-space blocks.",
            "Assignment binds a name to a value; it does not declare a fixed type. Integers represent whole numbers, floats represent decimal values, strings hold text, and booleans are True or False. Arithmetic operators combine numbers, while int(), float(), and str() convert compatible values. Use descriptive snake_case names and check types when input can vary.",
            "A string is an immutable sequence of characters. Indexing starts at zero, and a slice includes its start but excludes its end. input() returns text, even when the user types digits, so convert numeric input before arithmetic. An f-string evaluates expressions inside braces and is usually the clearest way to build formatted output.",
            "if and elif choose a branch based on a condition; else handles the remaining case. A for loop visits values from an iterable, and range(stop) produces values up to but not including stop. A while loop repeats while its condition is true. Update loop state carefully to avoid an infinite loop; break exits early and continue skips to the next iteration.",
            "A function packages a named task so it can be reused and tested. Parameters receive inputs, return sends a result back to the caller, and local variables exist only during that call. A default parameter value is used when an argument is omitted. Modules group code into files; import only the names or modules a file needs.",
            "A list is an ordered, mutable sequence: it keeps item order and can be changed after creation. Use an integer index to read or replace an item, append() to add at the end, and pop() or remove() to delete. A tuple is an ordered fixed collection; a dictionary maps unique keys to values. Choose a structure based on how the data will be accessed.",
            "A set stores unique hashable values and is useful for removing duplicates or testing membership. A comprehension builds a collection from an iterable with an optional condition. Exceptions represent runtime failures; catch only the errors you can handle, and keep the try block small so unexpected bugs are not hidden.",
            "A file is an external resource, so a with block should manage opening and closing it. pathlib provides portable paths, while json converts common Python data to and from JSON text. Specify an encoding for text files. Use read_text() for small files and stream larger files line by line.",
            "A class defines a kind of object; each instance stores its own state. __init__ initializes that state, and self refers to the current instance. Methods are functions that operate on an instance. Keep objects focused, prefer composition when one object uses another, and avoid a class when a small function or data structure is clearer.",
            "A recursive function solves a problem by calling itself on a smaller input. Every recursive path needs a base case that returns without another call, and each step must move toward that case. Calls use stack space, so deep recursion can exceed Python's recursion limit; an iterative solution may be better for large inputs.",
            "Big O describes how resource use grows with input size, ignoring machine-specific constants. A single pass is usually O(n), nested passes over the same input are often O(n squared), and halving the remaining search space gives O(log n). Constant-time lookup is O(1) on average for a dictionary. State assumptions when analyzing an algorithm.",
            "A stack follows last-in, first-out order: append pushes and pop removes the newest item. A queue follows first-in, first-out order; collections.deque supports efficient append and popleft operations. These structures model undo history, task queues, and breadth-first search. Choose operations that match the required order.",
            "A linked list stores values in nodes that point to other nodes; traversal follows links one by one, so finding an item is O(n). A hash table uses a hash to locate a bucket and powers Python dictionaries and sets; lookup is O(1) on average but can degrade with collisions. Use built-in dict unless node-level control is needed.",
            "Linear search checks values one at a time and works on unsorted input. Binary search compares with the middle and discards half the remaining range, giving O(log n), but it requires sorted data. Python's sorted() returns a new sorted list and list.sort() changes a list in place; prefer these tested built-ins in application code.",
            "A tree represents parent-child relationships; a graph represents general connections and may contain cycles. An adjacency list stores each node's neighbors. Breadth-first search uses a queue and finds a shortest path by edge count in an unweighted graph; depth-first search uses a stack or recursion to explore deeply. Track visited nodes to avoid cycles.",
            "Dynamic programming applies when subproblems repeat and their answers can be reused. Memoization stores results from recursive calls; tabulation builds answers from smaller cases in a table. Define the state, recurrence, and base cases before coding. Compare time and memory costs, and test small inputs to validate the recurrence.",
        ),
        "examples": (
            "print('Hello, Python!')\n\nRun the file with: python hello.py\nOutput: Hello, Python!",
            "name = 'Mina'\nage = 20\nactive = True\ntotal = age + 5\nprint(type(age).__name__, total)\n\nOutput: int 25",
            "text = 'Python'\nprint(text[0])\nprint(text[1:4])\nname = 'Mina'\nprint(f'Hello, {name}!')\n\nOutput: P / yth / Hello, Mina!",
            "for number in range(1, 4):\n    if number % 2 == 0:\n        print(number)\n\nOutput: 2",
            "def greet(name):\n    return f'Hello, {name}!'\n\nmessage = greet('Mina')\nprint(message)\n\nOutput: Hello, Mina!",
            "scores = [82, 91, 76]\nprint(scores[0])\nscores.append(88)\nremoved = scores.pop(1)\nfor score in scores:\n    print(score)\n\npoint = (4, 7)\nstudent = {'name': 'Mina', 'score': 91}\n\nOutput: 82, then 82, 76, 88 on separate lines; removed is 91.",
            "values = [1, 2, 2, 3]\nunique = {value for value in values}\nprint(sorted(unique))\n\ntry:\n    age = int('twenty')\nexcept ValueError:\n    age = 0\nprint(age)\n\nOutput: [1, 2, 3], then 0",
            "from pathlib import Path\npath = Path('notes.txt')\npath.write_text('Review Python', encoding='utf-8')\ntext = path.read_text(encoding='utf-8')\nprint(text)\n\nOutput: Review Python",
            "class Counter:\n    def __init__(self):\n        self.value = 0\n\n    def increment(self):\n        self.value += 1\n\ncounter = Counter()\ncounter.increment()\nprint(counter.value)\n\nOutput: 1",
            "def factorial(number):\n    if number <= 1:\n        return 1\n    return number * factorial(number - 1)\n\nprint(factorial(5))\n\nOutput: 120. The base case stops recursion; each call reduces the input.",
            "values = [3, 5, 8]\nfor value in values:\n    print(value)\n\nThis loop visits n items once, so its work grows linearly: O(n). A nested loop over the same values would usually be O(n squared).",
            "from collections import deque\nstack = [1, 2]\nstack.append(3)\nlast = stack.pop()\nqueue = deque([1, 2])\nqueue.append(3)\nfirst = queue.popleft()\nprint(last, first)\n\nOutput: 3 1",
            "class Node:\n    def __init__(self, value, next_node=None):\n        self.value = value\n        self.next = next_node\n\nhead = Node(10, Node(20))\nlookup = {'ada': 42}\nprint(head.next.value, lookup['ada'])\n\nOutput: 20 42",
            "from bisect import bisect_left\nvalues = [2, 4, 7, 9]\nposition = bisect_left(values, 7)\nprint(position)\nprint(sorted([9, 2, 7]))\n\nOutput: 2, then [2, 7, 9]. Binary search requires sorted input.",
            "from collections import deque\ngraph = {'A': ['B', 'C'], 'B': ['A'], 'C': ['A']}\nqueue = deque(['A'])\nvisited = {'A'}\nwhile queue:\n    node = queue.popleft()\n    for neighbor in graph[node]:\n        if neighbor not in visited:\n            visited.add(neighbor)\n            queue.append(neighbor)\nprint(sorted(visited))\n\nOutput: ['A', 'B', 'C']",
            "from functools import cache\n@cache\ndef fib(number):\n    if number < 2:\n        return number\n    return fib(number - 1) + fib(number - 2)\n\nprint(fib(10))\n\nOutput: 55. The cache reuses answers for repeated subproblems.",
        ),
    },
    {
        "title": "MySQL: Beginner to Practical SQL",
        "description": (
            "Learn relational database fundamentals and progress through SQL queries, "
            "joins, reporting, indexes, transactions, and a small schema project."
        ),
        "lessons": (
            ("Relational databases and MySQL", "Understand tables, rows, columns, and relationships. Connect to a MySQL server, select a database, and inspect schemas with SHOW and DESCRIBE."),
            ("Create databases and tables", "Create a database and define tables with suitable column types. Add primary keys, NOT NULL constraints, and defaults while considering how real values will be stored."),
            ("Insert, update, and delete rows", "Use INSERT, UPDATE, and DELETE to manage records. Preview the rows affected before changing data and use transactions when a change needs to be reversible."),
            ("Select, filter, and sort", "Build SELECT queries with WHERE, comparison operators, LIKE, IN, and BETWEEN. Sort results and limit output to answer focused questions."),
            ("NULL, expressions, and functions", "Handle missing values with IS NULL and COALESCE. Use aliases, calculated columns, and common string, numeric, and date functions to shape results."),
            ("Relationships and joins", "Connect related tables with primary and foreign keys. Write INNER and LEFT JOIN queries, qualify ambiguous columns, and check that joins do not multiply rows unexpectedly."),
            ("Aggregation and grouped reports", "Summarize records with COUNT, SUM, AVG, MIN, and MAX. Group results, filter groups with HAVING, and build a practical report from related tables."),
            ("Subqueries and common table expressions", "Use a subquery when a query depends on another result, and organize multi-step logic with a common table expression. Compare equivalent approaches for readability."),
            ("Indexes and query plans", "Learn how indexes speed up selected lookups and add write/storage costs. Use EXPLAIN to inspect a query plan and choose indexes based on actual filters and joins."),
            ("Transactions and data integrity", "Group changes with START TRANSACTION, COMMIT, and ROLLBACK. Explore atomicity, isolation at a practical level, and constraints that protect data from invalid states."),
            ("Schema design and normalization", "Model a small domain with one fact in each place. Identify repeating groups, use foreign keys, and normalize tables to reduce update anomalies without overcomplicating reads."),
            ("Views and the course project", "Create a view for a reusable report and document its purpose. Design a compact course-registration schema, populate sample rows, and answer questions with joins and aggregates."),
        ),
        "explanations": (
            "A relational database organizes data into tables with named columns and rows. A primary key uniquely identifies a row; a foreign key links it to a row in another table. MySQL is a database server that stores schemas and executes SQL. SHOW and DESCRIBE inspect the active database and table structure.",
            "CREATE TABLE defines a schema before rows are inserted. Choose a type that fits the data, mark required values NOT NULL, and use a primary key for identity. UNIQUE prevents duplicate values in a column or column group. Foreign keys can enforce valid relationships. AUTO_INCREMENT is convenient for generated integer identifiers.",
            "INSERT creates rows, UPDATE changes matching rows, and DELETE removes them. Always inspect the WHERE condition before UPDATE or DELETE because omitting it can affect every row. Use parameters in application queries instead of concatenating user input. Transactions make a group of changes reversible until committed.",
            "SELECT chooses output columns; FROM names the source table; WHERE filters individual rows; ORDER BY sorts; LIMIT caps the result count. LIKE supports pattern matching, with percent matching any sequence and underscore matching one character. IN checks a list of alternatives and BETWEEN includes both endpoints.",
            "SQL NULL means unknown or missing, not zero or an empty string. Comparisons with NULL do not behave like ordinary true/false comparisons, so use IS NULL or IS NOT NULL. COALESCE returns the first non-NULL value. Aliases name calculated output columns and make reports easier to read.",
            "A foreign key relates rows across tables, and JOIN combines matching rows. INNER JOIN keeps matches; LEFT JOIN keeps every left-side row and fills unmatched right-side columns with NULL. Joining one-to-many tables can multiply output rows, so check relationship cardinality and qualify columns with table names.",
            "Aggregate functions summarize groups of rows. GROUP BY forms groups, then COUNT, SUM, AVG, MIN, or MAX calculates one value per group. WHERE filters rows before aggregation; HAVING filters groups after aggregation. COUNT(*) counts rows, while COUNT(column) skips NULL values in that column.",
            "A subquery is a query nested inside another query and can provide a value or set of rows to filter against. A common table expression names an intermediate result with WITH, often making multi-step queries easier to read. Choose the clearest form and verify that inner queries return the expected number and shape of values.",
            "An index stores an auxiliary structure that helps the database find rows without scanning the whole table. Index columns used in selective filters and joins, but remember indexes consume storage and add work to writes. EXPLAIN shows the optimizer's planned access path; compare plans and timings rather than adding indexes blindly.",
            "A transaction groups database changes into one logical operation. COMMIT makes changes permanent; ROLLBACK cancels uncommitted changes. Atomicity means the group succeeds or fails together. Constraints such as NOT NULL, UNIQUE, and foreign keys reject invalid states even if application code has a bug.",
            "Normalization organizes facts so each is stored in an appropriate place, reducing inconsistent duplicate data. A student table should store student facts, while an enrollment table links students to courses. A composite key can prevent duplicate enrollment pairs. Design for clear ownership of facts, then add indexes for actual query patterns.",
            "A view is a named SELECT query that can simplify repeated reports and control which columns a consumer sees. In MySQL, a regular view generally reads from its underlying tables rather than storing a separate result. The capstone combines keys, joins, filters, aggregation, and a view into a small course-registration report.",
        ),
        "examples": (
            "SHOW DATABASES;\nUSE school;\nSHOW TABLES;\nDESCRIBE students;",
            "CREATE TABLE students (\n  id INT PRIMARY KEY AUTO_INCREMENT,\n  name VARCHAR(100) NOT NULL,\n  email VARCHAR(200) UNIQUE\n);",
            "INSERT INTO students (name, email) VALUES ('Mina', 'mina@example.com');\nUPDATE students SET name = 'Mina Lee' WHERE id = 1;\nDELETE FROM students WHERE id = 1;",
            "SELECT name, email\nFROM students\nWHERE name LIKE 'M%'\nORDER BY name\nLIMIT 10;",
            "SELECT name, COALESCE(phone, 'not provided') AS phone\nFROM students\nWHERE graduation_date IS NULL;",
            "SELECT students.name, courses.title\nFROM students\nJOIN enrollments ON enrollments.student_id = students.id\nJOIN courses ON courses.id = enrollments.course_id;",
            "SELECT course_id, COUNT(*) AS student_count\nFROM enrollments\nGROUP BY course_id\nHAVING COUNT(*) >= 5;",
            "WITH popular AS (\n  SELECT course_id, COUNT(*) AS total\n  FROM enrollments\n  GROUP BY course_id\n)\nSELECT * FROM popular WHERE total > 10;",
            "CREATE INDEX idx_students_email ON students(email);\nEXPLAIN SELECT * FROM students WHERE email = 'mina@example.com';",
            "START TRANSACTION;\nUPDATE accounts SET balance = balance - 10 WHERE id = 1;\nUPDATE accounts SET balance = balance + 10 WHERE id = 2;\nCOMMIT;",
            "CREATE TABLE enrollments (\n  student_id INT NOT NULL,\n  course_id INT NOT NULL,\n  enrolled_at DATE NOT NULL,\n  PRIMARY KEY (student_id, course_id)\n);",
            "CREATE VIEW course_totals AS\nSELECT course_id, COUNT(*) AS student_count\nFROM enrollments\nGROUP BY course_id;\nSELECT * FROM course_totals;",
        ),
    },
    {
        "title": "Applied AI: Machine Learning to RAG Agents",
        "description": (
            "A beginner-friendly, project-based path from data and machine learning "
            "to deep learning, NLP, LLMs, prompt design, RAG, and safe AI agents. "
            "Python basics are recommended; advanced calculus is not required."
        ),
        "lessons": (
            ("Start here: prerequisites and the AI map", "You should be comfortable with Python variables, functions, lists, dictionaries, and reading a CSV. Review averages, percentages, and simple charts as needed; advanced calculus is not required. Learn how AI, machine learning, deep learning, and generative AI relate, and choose one student problem for a course-long project."),
            ("Frame a problem and work responsibly with data", "Turn a broad idea into a question that can be checked with evidence. Identify the user, input, expected output, and failure cost. Use a small, permitted dataset; remove personal information and record where the data came from. Decide what a useful baseline would look like before selecting a model."),
            ("Prepare data and build a trustworthy baseline", "Inspect missing values, duplicates, labels, and data types. Split examples into training and test sets before fitting transformations so information cannot leak from the test set. Create a simple rule or majority-class baseline and keep a reproducible record of the split and preprocessing choices."),
            ("Supervised machine learning: regression and classification", "Learn how a model maps input features to a target using labeled examples. Compare a linear regression for numeric predictions with logistic regression or a decision tree for categories. Fit only on training data, make predictions on held-out examples, and explain which features might influence the result."),
            ("Evaluate models with the right metrics", "Accuracy alone can hide mistakes, especially when classes are imbalanced. Read a confusion matrix and compare precision, recall, and F1 for classification; use MAE for numeric predictions. Choose metrics based on the real impact of false positives and false negatives, and report test results honestly."),
            ("Unsupervised learning and useful representations", "Clustering groups examples without supplied labels; it does not automatically discover objectively true categories. Scale numeric features where appropriate, try a small clustering example, and inspect whether groups are useful to a person. Discuss how embeddings represent similarity and why a visualization is not proof of correctness."),
            ("Deep learning: neural networks by intuition", "A neural network combines layers of weighted calculations and nonlinear activations. Training adjusts weights to reduce a loss using gradients; you can understand this process without deriving calculus. Explore training versus validation loss, overfitting, and why more layers or data do not guarantee a better outcome."),
            ("NLP and transformers", "Natural language processing turns text into representations a computer can use. Compare tokenization and simple bag-of-words features with dense embeddings. Learn that transformer attention relates tokens to surrounding context, enabling models to process meaning beyond a fixed keyword list. Test examples with ambiguous words and discuss context."),
            ("LLMs: tokens, context, and limitations", "Large language models generate text by predicting likely next tokens from context. Learn what tokenization and context windows mean for cost and input limits. A fluent answer is not proof of truth: models can omit facts, invent sources, or reflect training-data bias. Treat external model calls as data sharing and check provider policies."),
            ("Prompt engineering for reliable tasks", "Write prompts with a clear task, relevant context, constraints, and an expected output format. Add a representative example when it helps, then test the prompt against normal, edge, and adversarial inputs. Ask for structured JSON only when your application validates it, and never treat prompt instructions as a substitute for authorization or server-side checks."),
            ("RAG: connect an LLM to trusted course material", "Retrieval-augmented generation searches a collection at question time and supplies relevant passages to a language model. Prepare permitted documents, split them into meaningful chunks, create embeddings, retrieve candidate passages, and ask the model to answer from those passages with source references. RAG adds context; it does not retrain the model."),
            ("Improve and evaluate a RAG workflow", "Build a small question set with expected evidence and acceptable answers. Check retrieval separately from generation: did the right passage appear, and did the response stay grounded in it? Test missing-answer questions, stale documents, and conflicting sources. Show citations that point to retrieved material and allow the system to say it does not know."),
            ("AI agents and tool use", "An agent is a model-driven loop that can choose from explicitly provided tools, observe results, and continue toward a goal. Start with a fixed workflow and add tool choice only when it provides value. Give tools narrow permissions, validate arguments, set step and time limits, log actions, and require human approval before consequential or irreversible actions."),
            ("Safety, privacy, bias, and human oversight", "Identify sensitive inputs, uneven error rates, prompt injection, unsafe retrieved content, and failure modes that affect students. Minimize stored data, separate trusted instructions from retrieved text, and never let a document grant permissions. Provide a route to a human, explain uncertainty, and test with varied examples before sharing the project."),
            ("Capstone: build a cited student study assistant", "Create a small study assistant over course notes that answers with source references and declines when the notes do not support an answer. Compare it with a simple keyword baseline. Submit the problem statement, data permissions, architecture, evaluation questions, error examples, safety decisions, and a short demo; do not upload private student records."),
        ),
        "explanations": (
            "Artificial intelligence is the broad goal of machine capability. Machine learning fits patterns from examples; deep learning uses multi-layer neural networks; generative AI creates new content. These categories overlap rather than replace one another. Start a project by identifying the user problem and evidence needed to judge a useful result.",
            "A good problem statement identifies a user, input, desired output, constraints, and the cost of a wrong answer. Define a measurable success criterion before selecting a model. Use data only when permitted, minimize personal information, and compare a model against a simple baseline so complexity has to earn its place.",
            "Inspect data before modeling: types, missing values, duplicates, label quality, and class balance all affect results. Split training and test examples before learning transformations; fitting a scaler or vocabulary on test data leaks information. Keep the split reproducible and use validation data for choices made during development.",
            "Supervised learning uses labeled examples. Features are the inputs and the target is the value or category to predict. Regression predicts a number; classification predicts a class. Fit the model only on training data, then make predictions on held-out examples. A model describes patterns in data, not necessarily causal relationships.",
            "A confusion matrix counts correct and incorrect classifications by class. Precision measures how many predicted positives were correct; recall measures how many actual positives were found; F1 balances them. Accuracy can be misleading when one class dominates. For regression, mean absolute error reports average absolute prediction error in target units.",
            "Unsupervised methods find structure without supplied target labels. Clustering assigns groups according to a chosen distance and representation; the groups are not automatically meaningful categories. Embeddings map items to vectors where distance can approximate similarity. Validate usefulness with examples and human judgment, not only a plot or score.",
            "A neural network layers weighted calculations and nonlinear activations. Training compares predictions with targets using a loss and adjusts weights to reduce that loss. Training performance alone can hide overfitting, so compare training and validation behavior. More layers, parameters, or data do not automatically produce a better or fairer system.",
            "Tokenization converts text into units the model can process. Transformer attention lets each token use information from surrounding tokens, which helps represent context. Bag-of-words features count tokens without their order; embeddings capture richer relationships. Test ambiguous phrases to see why context and evaluation examples matter.",
            "A large language model generates text by repeatedly predicting likely next tokens from its input context. The context window limits how much text fits in one request, and token counts affect latency and cost. Fluent output can still be false or incomplete. Verify important claims against trusted sources and handle external data according to provider policies.",
            "A useful prompt states the task, supplies relevant context, sets constraints, and describes the desired output. Examples can demonstrate the expected format. Test normal, edge, and adversarial inputs. Structured JSON is only a format request; parse it and validate every field before application code trusts it.",
            "Retrieval-augmented generation (RAG) finds relevant source passages at question time and supplies them to a language model. A typical pipeline prepares permitted documents, chunks them, embeds and indexes chunks, retrieves candidates, and asks the model to answer from those passages with citations. Retrieval adds context; it does not train the model.",
            "Evaluate retrieval and generation separately. Retrieval metrics ask whether useful evidence appears among the candidates; answer review checks correctness, grounding, citations, and appropriate abstention. Include answerable, ambiguous, missing-source, stale-source, and conflicting-source questions. A citation is useful only when it points to evidence supporting the associated claim.",
            "An agent uses a model to choose among explicitly available tools, observes tool results, and repeats until it finishes or reaches a limit. Start with a fixed workflow when possible. Validate tool names and arguments, grant narrow permissions, set time and step limits, log actions, and require approval for consequential changes.",
            "Responsible systems minimize collected data, protect secrets, test for uneven error rates, and keep a human path for consequential decisions. Retrieved text and user input are untrusted data, not authorization instructions. Validate every action server-side, explain uncertainty, and test prompt-injection and privacy failure cases before deployment.",
            "A cited study assistant combines a course document set, retrieval, a constrained generation step, and a user interface that shows sources. Compare it with keyword search using a fixed question set. Measure evidence retrieval and answer quality separately, and make the system state clearly when its sources do not support a course-specific claim.",
        ),
        "examples": (
            "AI is the broad field; machine learning fits patterns from examples; deep learning uses neural networks; generative AI creates new content.",
            "problem = {'user': 'student', 'input': 'course question', 'output': 'answer with sources', 'risk': 'unsupported answer'}",
            "from sklearn.model_selection import train_test_split\ntrain, test = train_test_split(rows, test_size=0.2, random_state=7)",
            "from sklearn.linear_model import LinearRegression\nmodel = LinearRegression().fit(train_features, train_targets)\npredictions = model.predict(test_features)",
            "from sklearn.metrics import classification_report\nprint(classification_report(actual_labels, predicted_labels))",
            "from sklearn.cluster import KMeans\nlabels = KMeans(n_clusters=3, random_state=7, n_init='auto').fit_predict(vectors)",
            "weighted_sum = weight * input_value + bias\nprediction = activation(weighted_sum)\n# Training adjusts weights to reduce a measured loss.",
            "text = 'A student studies Python'\ntokens = text.lower().split()\nprint(tokens)",
            "prompt_tokens = len(tokenize(question + retrieved_context))\nif prompt_tokens > context_limit:\n    retrieved_context = retrieved_context[:allowed_length]",
            "prompt = '''Task: explain the concept.\nContext: {lesson_text}\nConstraints: give one example and cite the lesson.'''",
            "question = 'How does a list work?'\npassages = retrieve(question, course_lessons)\nanswer = generate(question, context=passages, require_citations=True)",
            "for question, expected_source in evaluation_set:\n    retrieved = retrieve(question, lessons)\n    assert expected_source in retrieved  # evaluate retrieval separately",
            "while not done:\n    action = model.choose_tool(available_tools)\n    result = validate_and_run(action)\n    observe(result)",
            "allowed_tools = {'search_lessons'}\nif tool_name not in allowed_tools:\n    raise PermissionError('Tool is not allowed')",
            "question = 'What does the course say about lists?'\npassages = retrieve(question, lessons)\nif not passages:\n    answer = 'The course material does not cover this question.'",
        ),
    },
)

_ASSESSMENTS = (
    {
        "title": "Python Basics Assessment",
        "course": "Python Programming",
        "questions": (
            ("What does len([4, 7, 9]) return?", ["2", "3", "4", "An error"], 1),
            ("Which assignment stores the integer 12 in a variable named count?", ["count == 12", "count = 12", "int count = 12", "12 = count"], 1),
            ("What values does list(range(3)) produce?", ["[1, 2, 3]", "[0, 1, 2]", "[0, 1, 2, 3]", "[3]"], 1),
            ("What is 'Python'[1:4]?", ["Pyt", "yth", "tho", "ython"], 1),
            ("What does scores.append(95) do?", ["Adds 95 to the end", "Removes 95", "Sorts scores", "Returns the list length"], 0),
            ("For values = [10, 20, 30], what does values.pop(1) return?", ["10", "20", "30", "[10, 30]"], 1),
            ("How do you read the value for key 'name' from student = {'name': 'Ari'}?", ["student.name", "student[0]", "student['name']", "student->name"], 2),
            ("Which collection is immutable after creation?", ["list", "dict", "set", "tuple"], 3),
            ("What is set([1, 1, 2])?", ["{1, 2}", "{1, 1, 2}", "[1, 2]", "An error"], 0),
            ("Which keyword starts a conditional branch in Python?", ["when", "if", "case", "check"], 1),
            ("What does total become after: total = 0; for n in range(1, 4): total += n?", ["3", "5", "6", "10"], 2),
            ("What does a function's return statement do?", ["Sends a result to the caller", "Prints every local variable", "Repeats the function", "Imports a module"], 0),
            ("What type of value does input() return?", ["int", "float", "str", "bool"], 2),
            ("Which exception can int('hello') raise?", ["KeyError", "ValueError", "IndexError", "ImportError"], 1),
            ("Why use 'with open(path) as file:'?", ["It automatically closes the file", "It converts the file to JSON", "It sorts file lines", "It prevents all read errors"], 0),
            ("In an instance method, what does self refer to?", ["The current object", "The parent module", "The class name as text", "The method's return value"], 0),
            ("What must be true before using binary search on a list?", ["The list must be sorted", "The list must contain unique values", "The list must have even length", "The list must contain strings"], 0),
            ("A stack uses append() to push. Which operation removes the newest item?", ["pop()", "popleft()", "remove_last()", "dequeue()"], 0),
            ("Which operation removes the oldest item from collections.deque?", ["pop()", "popleft()", "discard()", "shift()"], 1),
            ("What is the time complexity of checking every item in a list once?", ["O(1)", "O(log n)", "O(n)", "O(n squared)"], 2),
        ),
    },
    {
        "title": "Python Foundations Assignment",
        "course": "Python Programming",
        "questions": (
            ("What type does len() return?", ["str", "int", "bool", "list"], 1),
            ("Which keyword defines a function in Python?", ["class", "return", "def", "import"], 2),
            ("What does list.append(value) do?", ["Adds value to the end", "Sorts the list", "Returns the list length", "Removes the first item"], 0),
            ("Which values are produced by range(3)?", ["1, 2, 3", "0, 1, 2", "0, 1, 2, 3", "3"], 1),
        ),
    },
    {
        "title": "Python Data Structures and Algorithms Assignment",
        "course": "Python Programming: Basics to DSA",
        "questions": (
            ("What must be true before binary search is used?", ["The values are sorted", "The list has even length", "All values are unique", "The list is linked"], 0),
            ("Which structure follows FIFO order?", ["Stack", "Queue", "Set", "Tree"], 1),
            ("Which structure is most directly used for depth-first traversal?", ["Queue", "Heap", "Stack", "Hash table"], 2),
            ("What is the typical time complexity of merge sort?", ["O(n)", "O(n log n)", "O(n squared)", "O(log n)"], 1),
        ),
    },
    {
        "title": "MySQL Fundamentals Assignment",
        "course": "MySQL: Beginner to Practical SQL",
        "questions": (
            ("Which SQL statement reads rows from a table?", ["SELECT", "INSERT", "UPDATE", "DROP"], 0),
            ("What does a primary key identify?", ["A database server", "A row uniquely", "A query result", "A table column type"], 1),
            ("Which clause filters rows before grouping?", ["ORDER BY", "HAVING", "WHERE", "LIMIT"], 2),
            ("How do you test for a missing SQL value?", ["= NULL", "IS NULL", "== NULL", "EMPTY()"], 1),
        ),
    },
    {
        "title": "MySQL Joins and Data Design Assignment",
        "course": "MySQL: Beginner to Practical SQL",
        "questions": (
            ("What does an INNER JOIN return?", ["Every row from the left table", "Rows with matching join values", "Only unmatched rows", "One random row"], 1),
            ("Which clause filters grouped results?", ["WHERE", "ORDER BY", "HAVING", "FROM"], 2),
            ("What is a common purpose of an index?", ["Speed up selected lookups", "Prevent all duplicate values", "Replace foreign keys", "Store query results permanently"], 0),
            ("Which statement cancels an uncommitted transaction?", ["COMMIT", "ROLLBACK", "SAVE", "RELEASE"], 1),
        ),
    },
    {
        "title": "Applied AI: ML and Evaluation Assignment",
        "course": "Applied AI: Machine Learning to RAG Agents",
        "questions": (
            ("Why keep a test set separate until final evaluation?", ["To increase training size", "To estimate performance on unseen data", "To remove the need for a baseline", "To guarantee fairness"], 1),
            ("Which metric can be more informative than accuracy for a rare positive class?", ["Precision and recall", "Training time", "Number of features", "File size"], 0),
            ("What is data leakage?", ["An unintended path for test information into training", "A model running out of memory", "A missing value in a CSV", "A dataset with too many rows"], 0),
            ("What does a neural network training process adjust?", ["Model weights to reduce a loss", "The test labels", "The user's permissions", "The CSV file name"], 0),
        ),
    },
    {
        "title": "Applied AI: LLMs and Prompt Design Assignment",
        "course": "Applied AI: Machine Learning to RAG Agents",
        "questions": (
            ("How does a generative language model produce text?", ["By retrieving a guaranteed fact database", "By predicting likely next tokens from context", "By executing every prompt as code", "By checking the internet automatically"], 1),
            ("What is a useful prompt ingredient for a specific task?", ["Clear task, relevant context, and output constraints", "A request to ignore all safety checks", "Only a longer prompt", "A hidden password"], 0),
            ("Does a fluent LLM answer prove that it is true?", ["Yes, fluency guarantees truth", "Only if it is long", "No, it still needs verification", "Only for technical topics"], 2),
            ("What should an app do with model-generated structured output?", ["Trust it without checking", "Validate it against the expected schema", "Use it as an authorization token", "Store it as executable code"], 1),
        ),
    },
    {
        "title": "Applied AI: RAG, Agents, and Responsible Use Assignment",
        "course": "Applied AI: Machine Learning to RAG Agents",
        "questions": (
            ("What does RAG add to a language-model request?", ["Retrieved relevant passages as context", "A guarantee that the model cannot err", "A new model training run", "Automatic user authorization"], 0),
            ("How should a RAG system handle unsupported questions?", ["Invent a likely answer", "Say the provided sources do not support an answer", "Hide its citations", "Repeat the prompt"], 1),
            ("What is a safer default for an agent tool?", ["Broad access to all user data", "Narrow permissions and validated arguments", "Unlimited steps", "No action log"], 1),
            ("What should happen before an irreversible agent action?", ["Human approval when the action is consequential", "Another model-generated prompt", "Disable validation", "Ignore the tool result"], 0),
        ),
    },
)


def seed_demo_data() -> None:
    if not os.getenv("ADMIN_EMAIL") or not os.getenv("ADMIN_PASSWORD"):
        raise RuntimeError("Set ADMIN_EMAIL and ADMIN_PASSWORD before seeding demo data")

    demo_password = os.getenv("DEMO_USER_PASSWORD", "DemoLearner2026!")
    if len(demo_password) < 8:
        raise RuntimeError("DEMO_USER_PASSWORD must contain at least 8 characters")

    Base.metadata.create_all(bind=engine)
    bootstrap_admin()

    with SessionLocal() as db:
        learners = []
        for index, name in enumerate(_LEARNERS, start=1):
            email = f"learner{index:02d}@example.com"
            learner = db.scalar(select(User).where(User.email == email))
            if learner is None:
                learner = User(
                    name=name,
                    email=email,
                    password_hash=hash_password(demo_password),
                )
                db.add(learner)
                db.flush()
            learners.append(learner)

        fresh_learner = learners[0]
        db.execute(
            delete(LessonCompletion).where(
                LessonCompletion.user_id == fresh_learner.id
            )
        )
        db.execute(delete(Enrollment).where(Enrollment.user_id == fresh_learner.id))

        course_data_to_seed = list(_COURSES)
        existing_python_course = db.scalar(
            select(Course).where(Course.title == "Python Programming")
        )
        if existing_python_course is not None:
            course_data_to_seed.insert(
                0, {**_COURSES[0], "title": existing_python_course.title}
            )

        seeded_courses = {}
        for course_index, course_data in enumerate(course_data_to_seed):
            demo_course = db.scalar(
                select(Course).where(Course.title == course_data["title"])
            )
            if demo_course is None:
                demo_course = Course(
                    title=course_data["title"],
                    description=course_data["description"],
                    instructor="VertexLearn Academy",
                )
                db.add(demo_course)
                db.flush()
            seeded_courses[demo_course.title] = demo_course

            lessons_by_position = {
                item.position: item
                for item in db.scalars(
                    select(Lesson).where(Lesson.course_id == demo_course.id)
                )
            }
            for position, ((title, content), example) in enumerate(
                zip(course_data["lessons"], course_data["examples"]), start=1
            ):
                lesson_item = lessons_by_position.get(position)
                explanations = course_data.get("explanations", ())
                explanation = explanations[position - 1] if explanations else ""
                base_content = content
                if lesson_item is not None and lesson_item.title == title:
                    base_content = lesson_item.content.split(
                        "\n\nConcepts and walkthrough:", 1
                    )[0].split("\n\nSyntax and example:", 1)[0]
                detailed_content = base_content
                if explanation:
                    detailed_content += f"\n\nConcepts and walkthrough:\n{explanation}"
                detailed_content += f"\n\nSyntax and example:\n{example}"
                if lesson_item is None:
                    lesson_item = Lesson(
                        course_id=demo_course.id,
                        title=title,
                        content=detailed_content,
                        position=position,
                    )
                    db.add(lesson_item)
                    lessons_by_position[position] = lesson_item
                elif lesson_item.title == title:
                    lesson_item.content = detailed_content
            db.flush()

            ordered_lessons = [
                lessons_by_position[position]
                for position in sorted(lessons_by_position)
            ]
            for learner_index, learner in enumerate(learners):
                enrollment = db.scalar(
                    select(Enrollment).where(
                        Enrollment.user_id == learner.id,
                        Enrollment.course_id == demo_course.id,
                    )
                )
                if learner_index == 0:
                    continue
                if enrollment is None:
                    db.add(Enrollment(user_id=learner.id, course_id=demo_course.id))

                completed_count = (learner_index * 3 + course_index) % (
                    len(ordered_lessons) + 1
                )
                for lesson_item in ordered_lessons[:completed_count]:
                    completion = db.scalar(
                        select(LessonCompletion).where(
                            LessonCompletion.user_id == learner.id,
                            LessonCompletion.lesson_id == lesson_item.id,
                        )
                    )
                    if completion is None:
                        db.add(
                            LessonCompletion(
                                user_id=learner.id,
                                lesson_id=lesson_item.id,
                            )
                        )

        python_basics_course = seeded_courses.get("Python Programming") or seeded_courses[
            "Python Programming: Basics to DSA"
        ]
        assessment_courses = {
            "Python Programming": python_basics_course,
            "Python Programming: Basics to DSA": seeded_courses[
                "Python Programming: Basics to DSA"
            ],
            "MySQL: Beginner to Practical SQL": seeded_courses[
                "MySQL: Beginner to Practical SQL"
            ],
            "Applied AI: Machine Learning to RAG Agents": seeded_courses[
                "Applied AI: Machine Learning to RAG Agents"
            ],
        }
        for assessment_data in _ASSESSMENTS:
            assessment_course = assessment_courses[assessment_data["course"]]
            demo_assessment = db.scalar(
                select(Assessment).where(
                    Assessment.course_id == assessment_course.id,
                    Assessment.title == assessment_data["title"],
                )
            )
            if demo_assessment is None:
                demo_assessment = Assessment(
                    title=assessment_data["title"],
                    course_id=assessment_course.id,
                    total_questions=len(assessment_data["questions"]),
                    passing_score=60,
                )
                db.add(demo_assessment)
                db.flush()

            demo_assessment.total_questions = len(assessment_data["questions"])

            existing_positions = set(
                db.scalars(
                    select(AssessmentQuestion.position).where(
                        AssessmentQuestion.assessment_id == demo_assessment.id
                    )
                )
            )
            for position, (prompt, options, correct_index) in enumerate(
                assessment_data["questions"], start=1
            ):
                if position not in existing_positions:
                    db.add(
                        AssessmentQuestion(
                            assessment_id=demo_assessment.id,
                            prompt=prompt,
                            options=options,
                            correct_option_index=correct_index,
                            position=position,
                        )
                    )

        db.commit()


if __name__ == "__main__":
    seed_demo_data()
    print("Demo data is ready: 1 configured admin, 10 demo learners, and 3 learning tracks.")
    print(f"Learner sign-in: learner01@example.com through learner10@example.com")
    print(f"Shared demo password: {os.getenv('DEMO_USER_PASSWORD', 'DemoLearner2026!')}")