import sqlite3

conn = sqlite3.connect('/Users/will/Documents/MoodleExport/python_sql_workflow/bootcamp.db')
cur = conn.cursor()

print("=== Learners with BOTH milestone types ===")
rows = cur.execute("""
    SELECT
        r.learner_id,
        q.course_id,
        SUM(CASE WHEN q.quiz_type = 'milestone_baseline_profile' THEN 1 ELSE 0 END) as has_baseline,
        SUM(CASE WHEN q.quiz_type = 'milestone_outcomes_profile' THEN 1 ELSE 0 END) as has_outcomes
    FROM responses r
    JOIN quizzes q ON r.quiz_id = q.quiz_id
    WHERE q.quiz_type IN ('milestone_baseline_profile', 'milestone_outcomes_profile')
    GROUP BY r.learner_id, q.course_id
    ORDER BY q.course_id, r.learner_id
""").fetchall()

both = [(lid, cid) for lid, cid, b, o in rows if b > 0 and o > 0]
baseline_only = [(lid, cid) for lid, cid, b, o in rows if b > 0 and o == 0]
outcomes_only = [(lid, cid) for lid, cid, b, o in rows if b == 0 and o > 0]

print(f"  Both baseline AND outcomes:  {len(both)} learners")
print(f"  Baseline only (no outcomes): {len(baseline_only)} learners")
print(f"  Outcomes only (no baseline): {len(outcomes_only)} learners")

print("\n=== Breakdown by course ===")
course_data = {}
for lid, cid, b, o in rows:
    if cid not in course_data:
        course_data[cid] = {'both': 0, 'base_only': 0, 'out_only': 0}
    if b > 0 and o > 0:
        course_data[cid]['both'] += 1
    elif b > 0:
        course_data[cid]['base_only'] += 1
    else:
        course_data[cid]['out_only'] += 1

print(f"  {'Course':<10} {'Both':<8} {'Base only':<12} {'Out only':<10}")
for cid in sorted(course_data.keys()):
    d = course_data[cid]
    print(f"  {cid:<10} {d['both']:<8} {d['base_only']:<12} {d['out_only']:<10}")

print(f"\n=== Employment track split for scoreable learners (both milestones) ===")
rows2 = cur.execute("""
    SELECT r.learner_id, q.course_id, q.quiz_type, q.quiz_name
    FROM responses r
    JOIN quizzes q ON r.quiz_id = q.quiz_id
    WHERE q.quiz_type IN ('milestone_baseline_profile', 'milestone_outcomes_profile')
    GROUP BY r.learner_id, q.course_id, q.quiz_type, q.quiz_name
""").fetchall()

scoreable = set((lid, cid) for lid, cid in both)
entrepreneur = set()
employed = set()
for lid, cid, qtype, qname in rows2:
    if (lid, cid) in scoreable:
        if 'Entrepreneur' in qname:
            entrepreneur.add((lid, cid))
        elif 'Employed' in qname:
            employed.add((lid, cid))

print(f"  Entrepreneur track: {len(entrepreneur)} learners")
print(f"  Employed track:     {len(employed)} learners")
print(f"  Unclassified:       {len(scoreable) - len(entrepreneur) - len(employed)}")

conn.close()
print("\nDone.")
