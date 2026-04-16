import sqlite3
import urllib.request
import json
import sys
from pathlib import Path

BASE_DIR = Path("/Users/will/Documents/MoodleExport/python_sql_workflow")
URL = "http://localhost:11434/api/generate"
MODEL = "gemma4:e4b"

# Load Rubric
with open(BASE_DIR / "SCORING_RUBRIC.md", "r") as f:
    rubric = f.read()

# Load Learner 190 data
conn = sqlite3.connect(BASE_DIR / "bootcamp.db")
c = conn.cursor()
c.execute("""
    SELECT r.question_number, r.learner_answer
    FROM responses r
    JOIN quizzes q ON r.quiz_id = q.quiz_id
    WHERE q.quiz_type = 'usage_reflection'
      AND q.course_id = 48
      AND r.learner_id = 190
    ORDER BY q.quiz_id
""")
rows = c.fetchall()
conn.close()

reflections_text = "Learner 190 Reflections (Chronological):\n"
for i, row in enumerate(rows):
    reflections_text += f"\nWeek {i+1}:\n{row[1]}\n"

prompt = f"""
You are an expert AI educational data analyst evaluating learner usage diaries.
We are using a dual-framework rubric to score the learner's journey.

{rubric}

Here are the chronological weekly reflections for Learner 190:

{reflections_text}

Analyze these reflections. Please provide:
1. A week-by-week analysis showing the Sophistication Score (1-4) for each week and short reasoning extracting the tools and concepts mentioned.
2. A short synthesis of their overall Narrative Arc.
3. Their Overall Bloom's Taxonomy Ceiling (L1-L6) with reasoning.
"""

payload = {
    "model": MODEL,
    "prompt": prompt,
    "stream": False
}

print("Querying Gemma4:e4b... please wait.", flush=True)
try:
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(URL, data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=120) as response:
        if response.status == 200:
            result = json.loads(response.read().decode('utf-8'))
            raw_text = result.get("response")
            # Save raw output to file for the user to view
            with open("gemma_raw_output_190.md", "w") as out_file:
                out_file.write(raw_text)
            print("Successfully saved output to gemma_raw_output_190.md")
        else:
            print("API Error:", response.status)
except Exception as e:
    print("Request failed:", str(e))
