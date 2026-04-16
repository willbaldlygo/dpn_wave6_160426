import sqlite3

conn = sqlite3.connect('/Users/will/Documents/MoodleExport/python_sql_workflow/bootcamp.db')
cur = conn.cursor()

sections = [
    ("BASELINE — Entrepreneur",    "milestone_baseline_profile",  "%Entrepreneur%"),
    ("BASELINE — Employed",        "milestone_baseline_profile",  "%Employed%"),
    ("OUTCOMES — Entrepreneur",    "milestone_outcomes_profile",  "%Entrepreneur%"),
    ("OUTCOMES — Employed",        "milestone_outcomes_profile",  "%Employed%"),
]

for label, quiz_type, name_pattern in sections:
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    rows = cur.execute("""
        SELECT DISTINCT r.question_number, r.question_text
        FROM responses r
        JOIN quizzes q ON r.quiz_id = q.quiz_id
        WHERE q.quiz_type = ?
          AND q.quiz_name LIKE ?
        ORDER BY r.question_number
    """, (quiz_type, name_pattern)).fetchall()
    if not rows:
        print("  (no results)")
    for qn, qt in rows:
        print(f"  Q{int(qn) if qn else '?'}: {qt}")

conn.close()
print("\nDone.")
