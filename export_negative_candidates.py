import sqlite3
import json
import re

conn = sqlite3.connect('bootcamp.db')
c = conn.cursor()

query = """
SELECT r.learner_id, q.course_id, r.learner_answer
FROM responses r
JOIN quizzes q ON r.quiz_id = q.quiz_id
WHERE q.quiz_type = 'usage_reflection'
"""
c.execute(query)
rows = c.fetchall()
conn.close()

negative_patterns = [
    r'\bbad\b', r'\buseless\b', r'\bterrible\b', r'\bwaste of time\b', 
    r'\bfrustrat\w*', r'\bpointless\b', r'\bhate\b', r'\bdisappoint\w*', 
    r'\bstruggle\b', r'\bhard\b', r'\bdifficult\b', r'\bnegative\b',
    r'\bconfus\w*', r'\bboring\b', r'\boverwhelm\w*', r'\btoo much\b',
    r'\bnot helpful\b', r'\bannoy\w*'
]

candidates = []
for row in rows:
    ans = row[2].lower() if row[2] else ""
    for pat in negative_patterns:
        if re.search(pat, ans):
            candidates.append({"learner_id": row[0], "course_id": row[1], "answer": row[2]})
            break

with open('negative_candidates.json', 'w') as f:
    json.dump(candidates, f, indent=2)

print(f"Exported {len(candidates)} candidates.")
