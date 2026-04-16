import sqlite3
import urllib.request
import json
import time
import csv
from pathlib import Path

BASE_DIR = Path("/Users/will/Documents/MoodleExport/python_sql_workflow")
DB_PATH = BASE_DIR / "bootcamp.db"
RUBRIC_PATH = BASE_DIR / "SCORING_RUBRIC.md"
CSV_OUT_PATH = BASE_DIR / "layer2_layer3_analysis.csv"

URL = "http://localhost:11434/api/generate"
MODEL = "gemma4:e4b"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS learner_arcs (
            learner_id INTEGER,
            course_id INTEGER,
            evaluator_model TEXT,
            raw_analysis TEXT,
            PRIMARY KEY (learner_id, course_id, evaluator_model)
        )
    ''')
    conn.commit()
    conn.close()

def export_to_csv():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT learner_id, course_id, evaluator_model, raw_analysis FROM learner_arcs ORDER BY course_id, learner_id")
    rows = c.fetchall()
    conn.close()

    if not rows:
        return

    with open(CSV_OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["learner_id", "course_id", "evaluator_model", "raw_analysis"])
        writer.writerows(rows)

def get_target_learners():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Find all unique learners who have usage_reflection responses
    c.execute("""
        SELECT DISTINCT r.learner_id, q.course_id 
        FROM responses r
        JOIN quizzes q ON r.quiz_id = q.quiz_id
        WHERE q.quiz_type = 'usage_reflection'
    """)
    all_learners = c.fetchall()

    # Find already processed
    c.execute("SELECT learner_id, course_id FROM learner_arcs WHERE evaluator_model = ?", (MODEL,))
    processed = set(c.fetchall())
    conn.close()

    targets = [l for l in all_learners if l not in processed]
    return targets, len(all_learners), len(processed)

def fetch_reflections(learner_id, course_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT r.question_number, r.learner_answer
        FROM responses r
        JOIN quizzes q ON r.quiz_id = q.quiz_id
        WHERE q.quiz_type = 'usage_reflection' AND r.learner_id = ? AND q.course_id = ?
        ORDER BY q.quiz_id
    """, (learner_id, course_id))
    rows = c.fetchall()
    conn.close()
    return rows

def save_result(learner_id, course_id, analysis_text):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO learner_arcs (learner_id, course_id, evaluator_model, raw_analysis)
        VALUES (?, ?, ?, ?)
    """, (learner_id, course_id, MODEL, analysis_text))
    conn.commit()
    conn.close()

def main():
    print("Initializing database and CSV export pipeline...")
    init_db()
    
    with open(RUBRIC_PATH, "r", encoding="utf-8") as f:
        rubric = f.read()

    targets, total_learners, processed_count = get_target_learners()
    export_to_csv() # Generate initial File

    print(f"\n--- Batch Pipeline Status ---")
    print(f"Total learners with reflections: {total_learners}")
    print(f"Already processed: {processed_count}")
    print(f"Pending evaluation: {len(targets)}")
    print(f"Model used: {MODEL}")
    print(f"-----------------------------\n")

    if not targets:
        print("All target learners have been successfully processed!")
        return

    for i, (learner_id, course_id) in enumerate(targets, 1):
        print(f"[{i}/{len(targets)}] Evaluating Learner {learner_id} (Course {course_id})...", end=" ", flush=True)
        
        reflections = fetch_reflections(learner_id, course_id)
        ref_text = f"Learner {learner_id} Reflections (Chronological):\n"
        for week_idx, row in enumerate(reflections):
            ref_text += f"\nWeek {week_idx+1}:\n{row[1]}\n"

        prompt = f"""
You are an expert AI educational data analyst evaluating learner usage diaries.
We are using a dual-framework rubric to score the learner's journey.

{rubric}

Here are the chronological weekly reflections for Learner {learner_id}:

{ref_text}

Analyze these reflections. Please provide:
1. A week-by-week analysis showing the Sophistication Score (1-4) for each week and short reasoning extracting the tools and concepts mentioned.
2. A short synthesis of their overall Narrative Arc.
3. Their Overall Bloom's Taxonomy Ceiling (L1-L6) with reasoning.
"""
        
        payload = {"model": MODEL, "prompt": prompt, "stream": False}
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(URL, data=data, headers={'Content-Type': 'application/json'})
        
        start_time = time.time()
        try:
            with urllib.request.urlopen(req, timeout=300) as response:
                if response.status == 200:
                    result = json.loads(response.read().decode('utf-8'))
                    analysis = result.get("response")
                    
                    save_result(learner_id, course_id, analysis)
                    export_to_csv() # Refresh CSV state on every successful save

                    elapsed = time.time() - start_time
                    print(f"DONE (took {elapsed:.1f}s)")
                else:
                    print(f"FAILED (API ERROR: {response.status})")
        except urllib.error.URLError as e:
            print(f"FAILED (Connection Error: Is Ollama running? - {e.reason})")
            print("\nPipeline stopped due to connection error. Fix Ollama and rerun this script to resume.")
            break
        except Exception as e:
            print(f"FAILED (Error: {str(e)})")

    print("\nBatch process run completed. CSV file 'layer2_layer3_analysis.csv' has been updated.")

if __name__ == "__main__":
    main()
