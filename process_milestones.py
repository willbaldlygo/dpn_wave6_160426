import sqlite3
import urllib.request
import json
import time
import csv
import os
import re
import ssl
from pathlib import Path
import concurrent.futures

BASE_DIR = Path("/Users/will/Documents/MoodleExport/python_sql_workflow")
DB_PATH = BASE_DIR / "bootcamp.db"
RUBRIC_PATH = BASE_DIR / "SCORING_RUBRIC.md"
CSV_OUT_PATH = BASE_DIR / "milestone_matrix.csv"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_NAME = "gemini-2.5-flash"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS milestone_arcs (
            learner_id INTEGER,
            course_id INTEGER,
            evaluator_model TEXT,
            raw_analysis TEXT,
            PRIMARY KEY (learner_id, course_id, evaluator_model)
        )
    ''')
    conn.commit()
    conn.close()

def get_target_learners():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT r.learner_id, q.course_id 
        FROM responses r
        JOIN quizzes q ON r.quiz_id = q.quiz_id
        WHERE q.quiz_type IN ('milestone_baseline_profile', 'milestone_outcomes_profile')
        GROUP BY r.learner_id, q.course_id
        HAVING COUNT(DISTINCT q.quiz_type) = 2
    """)
    all_learners = c.fetchall()

    c.execute("SELECT learner_id, course_id FROM milestone_arcs WHERE evaluator_model = ?", (MODEL_NAME,))
    processed = set(c.fetchall())
    conn.close()

    targets = [l for l in all_learners if l not in processed]
    targets.sort(key=lambda x: (x[1], x[0]))
    return targets, len(all_learners), len(processed)

def fetch_milestones(learner_id, course_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        SELECT r.question_text, r.learner_answer
        FROM responses r
        JOIN quizzes q ON r.quiz_id = q.quiz_id
        WHERE q.quiz_type = 'milestone_baseline_profile' AND r.learner_id = ? AND q.course_id = ?
        ORDER BY r.question_number
    """, (learner_id, course_id))
    baseline = c.fetchall()
    
    c.execute("""
        SELECT r.question_text, r.learner_answer
        FROM responses r
        JOIN quizzes q ON r.quiz_id = q.quiz_id
        WHERE q.quiz_type = 'milestone_outcomes_profile' AND r.learner_id = ? AND q.course_id = ?
        ORDER BY r.question_number
    """, (learner_id, course_id))
    outcomes = c.fetchall()
    
    conn.close()
    return baseline, outcomes

def save_result(learner_id, course_id, analysis_text):
    conn = sqlite3.connect(DB_PATH, timeout=10.0) # Handle thread locks
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO milestone_arcs (learner_id, course_id, evaluator_model, raw_analysis)
        VALUES (?, ?, ?, ?)
    """, (learner_id, course_id, MODEL_NAME, analysis_text))
    conn.commit()
    conn.close()

def process_single_learner(learner_id, course_id, rubric):
    baseline, outcomes = fetch_milestones(learner_id, course_id)
    
    ref_text = f"--- START OF LEARNER {learner_id} DATA ---\n\n"
    ref_text += "## BASELINE PROFILE (Start of Bootcamp)\n"
    for idx, (q, a) in enumerate(baseline):
        ref_text += f"**Q{idx+1}: {q}**\nA: {a}\n\n"
        
    ref_text += "## OUTCOMES PROFILE (End of Bootcamp)\n"
    for idx, (q, a) in enumerate(outcomes):
        ref_text += f"**Q{idx+1}: {q}**\nA: {a}\n\n"
        
    prompt = f"""
You are an expert AI educational data analyst evaluating learner milestone surveys from an AI bootcamp.
We are using a dual-framework rubric to score the learner's journey.

{rubric}

Here are the baseline (start) and outcomes (end) reflections for Learner {learner_id}:

{ref_text}

Analyze these reflections. Please provide your evaluation EXACTLY in the following format so it can be parsed:

BASELINE SOPHISTICATION: [1, 2, 3, or 4]
OUTCOMES SOPHISTICATION: [1, 2, 3, or 4]
BASELINE BLOOM: [L1, L2, L3, L4, L5, or L6]
OUTCOMES BLOOM: [L1, L2, L3, L4, L5, or L6]
NARRATIVE ARC:
[Provide a short synthesis comparing their starting point to their endpoint, extracting specific tools or concepts they adopted, and explaining the shift in their capability].
"""
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(API_URL, data=data, headers={'Content-Type': 'application/json'})
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    max_retries = 3
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=120, context=ctx) as response:
                if response.status == 200:
                    result = json.loads(response.read().decode('utf-8'))
                    num_candidates = len(result.get("candidates", []))
                    if num_candidates > 0:
                        analysis = result["candidates"][0]["content"]["parts"][0]["text"]
                        save_result(learner_id, course_id, analysis)
                        return f"Success Learner {learner_id}"
                    return f"Failed Learner {learner_id}: No candidates"
        except urllib.error.HTTPError as e:
            if e.code == 429: # Rate Limited
                time.sleep((attempt + 1) * 15) # Backoff (15s, 30s, 45s)
                continue
            return f"Failed Learner {learner_id}: HTTP {e.code}"
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(5)
                continue
            return f"Failed Learner {learner_id}: {str(e)}"
            
    return f"Failed Learner {learner_id}: Max retries reached"

def export_to_csv():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT learner_id, course_id, raw_analysis FROM milestone_arcs WHERE evaluator_model = ? ORDER BY course_id, learner_id", (MODEL_NAME,))
    rows = c.fetchall()
    
    out_data = []
    
    for row in rows:
        lid, cid, text = row
        
        base_soph = base_bloom = out_soph = out_bloom = None
        
        match = re.search(r'BASELINE SOPHISTICATION:\s*(\d)', text, re.IGNORECASE)
        if match: base_soph = int(match.group(1))
            
        match = re.search(r'OUTCOMES SOPHISTICATION:\s*(\d)', text, re.IGNORECASE)
        if match: out_soph = int(match.group(1))
            
        match = re.search(r'BASELINE BLOOM:\s*(L[1-6])', text, re.IGNORECASE)
        if match: base_bloom = match.group(1).upper()
            
        match = re.search(r'OUTCOMES BLOOM:\s*(L[1-6])', text, re.IGNORECASE)
        if match: out_bloom = match.group(1).upper()
            
        narrative_match = re.search(r'NARRATIVE ARC:(.*)', text, re.IGNORECASE | re.DOTALL)
        narrative = narrative_match.group(1).strip() if narrative_match else text
        
        baseline, outcomes = fetch_milestones(lid, cid)
        
        base_dict = {f"Q: {q}": a for q, a in baseline}
        out_dict = {f"Q: {q}": a for q, a in outcomes}
        
        out_data.append([
            lid, cid, 
            base_soph, out_soph, 
            base_bloom, out_bloom, 
            narrative, 
            json.dumps(base_dict), 
            json.dumps(out_dict)
        ])
        
    with open(CSV_OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["learner_id", "course_id", "base_sophistication", "out_sophistication", "base_bloom", "out_bloom", "progression_narrative", "raw_baseline_json", "raw_outcomes_json"])
        writer.writerows(out_data)

    conn.close()

def main():
    if not GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY environment variable not set.")
        return

    init_db()
    with open(RUBRIC_PATH, "r", encoding="utf-8") as f:
        rubric = f.read()

    targets, total_learners, processed_count = get_target_learners()
    export_to_csv()

    print(f"\n--- Gemini Batch Pipeline Status ---")
    print(f"Pending evaluation: {len(targets)}")
    print(f"Model used: {MODEL_NAME} (Asynchronous / 5 Threads)")
    
    if not targets:
        print("All target learners have been successfully processed!")
        return

    # Multithreading Execution
    threads = 5  # Safe default to avoid instantly hitting free tier rate limits
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {executor.submit(process_single_learner, t[0], t[1], rubric): t for t in targets}
        
        completed = 0
        for future in concurrent.futures.as_completed(futures):
            completed += 1
            res = future.result()
            print(f"[{completed:03d}/{len(targets):03d}] {res}")

    total_time = time.time() - start_time
    print(f"\nBatch process run completed in {total_time:.1f} seconds.")
    
    print("Writing CSV...")
    export_to_csv()
    print(f"CSV exported to {CSV_OUT_PATH}")

if __name__ == "__main__":
    main()
