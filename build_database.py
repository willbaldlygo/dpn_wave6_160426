"""
build_database.py
=================
Ingests all_quiz_responses_clean.csv and builds bootcamp.db — a SQLite
relational database with four tables:

    quiz_types   controlled vocabulary for quiz classification
    courses      one row per Moodle course ID
    quizzes      one row per unique quiz (name + type + course)
    responses    one row per learner answer (the main data)

Run from the python_sql_workflow directory:
    python3 build_database.py

Requirements: Python 3.8+, pandas
Install pandas if needed:  pip install pandas
"""

import sqlite3
import pandas as pd
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent
CSV_PATH = BASE_DIR / "all_quiz_responses_clean.csv"
DB_PATH  = BASE_DIR / "bootcamp.db"

# ── 1. Load CSV ────────────────────────────────────────────────────────────────

print("Loading CSV...")

df = pd.read_csv(
    CSV_PATH,
    encoding="utf-8-sig",   # handles the Excel BOM character
    dtype=str,               # load everything as text first; cast later
    keep_default_na=False,   # don't convert empty strings to NaN yet
)

# Drop entirely empty rows (Excel export artefact at end of file)
df = df.dropna(how="all")
df = df[df["learner_id"].str.strip() != ""]

print(f"  Loaded {len(df):,} rows, {len(df.columns)} columns")
print(f"  Columns: {list(df.columns)}")

# ── 2. Normalise column values ─────────────────────────────────────────────────

# Strip whitespace from all string columns
df = df.apply(lambda col: col.str.strip() if col.dtype == object else col)

# Cast numeric columns — coerce errors to NaN (handles empty strings cleanly)
df["learner_id"]      = pd.to_numeric(df["learner_id"],      errors="coerce")
df["course_id"]       = pd.to_numeric(df["course_id"],       errors="coerce")
df["question_number"] = pd.to_numeric(df["question_number"], errors="coerce")
df["mark_awarded"]    = pd.to_numeric(df["mark_awarded"],     errors="coerce")
df["max_mark"]        = pd.to_numeric(df["max_mark"],         errors="coerce")

# Convert flag_review to boolean: any non-empty string = True
df["flag_review"] = df["flag_review"].apply(lambda x: bool(x and x.strip()))

# Drop rows where core identifiers are missing
df = df.dropna(subset=["learner_id", "course_id"])
df["learner_id"] = df["learner_id"].astype(int)
df["course_id"]  = df["course_id"].astype(int)

print(f"  After cleaning: {len(df):,} data rows")

# ── 3. Build lookup tables ─────────────────────────────────────────────────────

# quiz_types: your controlled vocabulary
quiz_type_rows = [
    (1, "milestone_baseline_profile", "Day 1 intake quiz, split by employment status"),
    (2, "milestone_outcomes_profile", "End-of-course review, split by employment status"),
    (3, "knowledge_check",            "Weekly MC/T&F comprehension quiz — markable"),
    (4, "tools_inventory",            "AI tools currently in use"),
    (5, "usage_reflection",           "Weekly open-text AI usage diary"),
    (6, "unclassified",               "Needs manual review"),
]

# courses: one row per unique course_id
course_ids  = sorted(df["course_id"].unique())
course_rows = [(int(cid),) for cid in course_ids]
print(f"  Found {len(course_rows)} unique courses: {[r[0] for r in course_rows]}")

# quizzes: one row per unique (quiz_name, quiz_type, course_id) combination
quiz_df = (
    df[["quiz_name", "quiz_type", "course_id"]]
    .drop_duplicates()
    .sort_values(["course_id", "quiz_name"])
    .reset_index(drop=True)
)
quiz_df.insert(0, "quiz_id", range(1, len(quiz_df) + 1))
print(f"  Found {len(quiz_df)} unique quizzes")

# Lookup dict: (quiz_name, quiz_type, course_id) → quiz_id
quiz_lookup = {
    (row["quiz_name"], row["quiz_type"], int(row["course_id"])): row["quiz_id"]
    for _, row in quiz_df.iterrows()
}

# ── 4. Build responses table ───────────────────────────────────────────────────

responses_df = df.copy()

responses_df["quiz_id"] = responses_df.apply(
    lambda row: quiz_lookup.get(
        (row["quiz_name"], row["quiz_type"], int(row["course_id"]))
    ),
    axis=1,
)

responses_df = responses_df[[
    "learner_id",
    "quiz_id",
    "question_number",
    "question_text",
    "learner_answer",
    "correct_answer",
    "mark_awarded",
    "max_mark",
    "flag_review",
]].reset_index(drop=True)

responses_df.insert(0, "response_id", range(1, len(responses_df) + 1))
print(f"  Built {len(responses_df):,} response rows")

# ── 5. Write to SQLite ─────────────────────────────────────────────────────────

print(f"\nWriting to {DB_PATH}...")

if DB_PATH.exists():
    DB_PATH.unlink()
    print("  Removed existing bootcamp.db for clean rebuild")

conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()

cur.execute("""
    CREATE TABLE quiz_types (
        type_id     INTEGER PRIMARY KEY,
        type_code   TEXT UNIQUE NOT NULL,
        description TEXT
    )
""")
cur.executemany("INSERT INTO quiz_types VALUES (?, ?, ?)", quiz_type_rows)

cur.execute("""
    CREATE TABLE courses (
        course_id   INTEGER PRIMARY KEY,
        course_name TEXT
    )
""")
cur.executemany("INSERT INTO courses (course_id) VALUES (?)", course_rows)

cur.execute("""
    CREATE TABLE quizzes (
        quiz_id   INTEGER PRIMARY KEY,
        quiz_name TEXT NOT NULL,
        quiz_type TEXT NOT NULL,
        course_id INTEGER NOT NULL REFERENCES courses(course_id)
    )
""")
quiz_df[["quiz_id", "quiz_name", "quiz_type", "course_id"]].to_sql(
    "quizzes", conn, if_exists="append", index=False
)

cur.execute("""
    CREATE TABLE responses (
        response_id     INTEGER PRIMARY KEY,
        learner_id      INTEGER NOT NULL,
        quiz_id         INTEGER NOT NULL REFERENCES quizzes(quiz_id),
        question_number INTEGER,
        question_text   TEXT,
        learner_answer  TEXT,
        correct_answer  TEXT,
        mark_awarded    REAL,
        max_mark        REAL,
        flag_review     BOOLEAN DEFAULT FALSE
    )
""")
responses_df.to_sql("responses", conn, if_exists="append", index=False)

# ── 6. Verification queries ────────────────────────────────────────────────────

print("\nVerification:")

checks = [
    ("Total responses",      "SELECT COUNT(*) FROM responses"),
    ("Unique learners",      "SELECT COUNT(DISTINCT learner_id) FROM responses"),
    ("Unique courses",       "SELECT COUNT(*) FROM courses"),
    ("Unique quizzes",       "SELECT COUNT(*) FROM quizzes"),
    ("Flagged rows",         "SELECT COUNT(*) FROM responses WHERE flag_review = 1"),
    ("Rows missing quiz_id", "SELECT COUNT(*) FROM responses WHERE quiz_id IS NULL"),
]

for label, query in checks:
    result = cur.execute(query).fetchone()[0]
    print(f"  {label:<25} {result:,}")

print("\nRows per quiz type:")
rows = cur.execute("""
    SELECT q.quiz_type, COUNT(*) as n
    FROM responses r
    JOIN quizzes q ON r.quiz_id = q.quiz_id
    GROUP BY q.quiz_type
    ORDER BY n DESC
""").fetchall()
for quiz_type, count in rows:
    print(f"  {quiz_type:<40} {count:,}")

conn.commit()
conn.close()

print(f"\nDone. Database written to: {DB_PATH}")
