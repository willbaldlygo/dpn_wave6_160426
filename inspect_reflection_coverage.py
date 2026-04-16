import sqlite3

conn = sqlite3.connect('/Users/will/Documents/MoodleExport/python_sql_workflow/bootcamp.db')
cur = conn.cursor()

print("=== Usage reflection rows per course ===")
rows = cur.execute("""
    SELECT q.course_id, COUNT(*) as reflection_rows,
           COUNT(DISTINCT r.learner_id) as learners_with_reflections
    FROM responses r
    JOIN quizzes q ON r.quiz_id = q.quiz_id
    WHERE q.quiz_type = 'usage_reflection'
    GROUP BY q.course_id
    ORDER BY q.course_id
""").fetchall()
for course_id, refl_rows, learners in rows:
    print(f"  Course {course_id}: {refl_rows} rows, {learners} learners")

print("\n=== Total learners per course (for context) ===")
rows = cur.execute("""
    SELECT q.course_id, COUNT(DISTINCT r.learner_id) as total_learners
    FROM responses r
    JOIN quizzes q ON r.quiz_id = q.quiz_id
    GROUP BY q.course_id
    ORDER BY q.course_id
""").fetchall()
for course_id, total in rows:
    print(f"  Course {course_id}: {total} learners total")

print("\n=== Avg reflections per learner (courses with reflection data) ===")
rows = cur.execute("""
    SELECT q.course_id,
           COUNT(*) as total_rows,
           COUNT(DISTINCT r.learner_id) as learners,
           ROUND(CAST(COUNT(*) AS FLOAT) / COUNT(DISTINCT r.learner_id), 1) as avg_per_learner
    FROM responses r
    JOIN quizzes q ON r.quiz_id = q.quiz_id
    WHERE q.quiz_type = 'usage_reflection'
    GROUP BY q.course_id
    ORDER BY q.course_id
""").fetchall()
for course_id, total, learners, avg in rows:
    print(f"  Course {course_id}: {avg} reflections/learner avg ({total} rows, {learners} learners)")

print("\n=== Courses with BOTH milestone types AND reflection data ===")
rows = cur.execute("""
    SELECT q.course_id,
           SUM(CASE WHEN q.quiz_type = 'milestone_baseline_profile' THEN 1 ELSE 0 END) as has_baseline,
           SUM(CASE WHEN q.quiz_type = 'milestone_outcomes_profile' THEN 1 ELSE 0 END) as has_outcomes,
           SUM(CASE WHEN q.quiz_type = 'usage_reflection' THEN 1 ELSE 0 END) as has_reflection
    FROM responses r
    JOIN quizzes q ON r.quiz_id = q.quiz_id
    GROUP BY q.course_id
    ORDER BY q.course_id
""").fetchall()
print(f"  {'Course':<10} {'Baseline':<12} {'Outcomes':<12} {'Reflection':<12}")
for course_id, base, out, refl in rows:
    b = "YES" if base > 0 else "-"
    o = "YES" if out > 0 else "-"
    r = "YES" if refl > 0 else "-"
    print(f"  {course_id:<10} {b:<12} {o:<12} {r:<12}")

conn.close()
print("\nDone.")
