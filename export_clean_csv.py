import sqlite3
import csv
import re
import json
from pathlib import Path

BASE_DIR = Path("/Users/will/Documents/MoodleExport/python_sql_workflow")
DB_PATH = BASE_DIR / "bootcamp.db"
CSV_OUT_PATH = BASE_DIR / "layer2_layer3_clean_matrix.csv"

def export_clean():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 1. Fetch all evaluations
    c.execute("SELECT learner_id, course_id, raw_analysis FROM learner_arcs")
    eval_rows = c.fetchall()
    
    # 2. Map raw responses to learners
    # We fetch all usage_reflection answers for ALL learners to avoid N queries
    c.execute("""
        SELECT r.learner_id, r.learner_answer 
        FROM responses r
        JOIN quizzes q ON r.quiz_id = q.quiz_id
        WHERE q.quiz_type = 'usage_reflection'
        ORDER BY r.learner_id, q.quiz_id
    """)
    ans_data = c.fetchall()
    answers_map = {}
    for lid, ans in ans_data:
        if lid not in answers_map:
            answers_map[lid] = []
        answers_map[lid].append(ans)

    clean_data = []
    
    for learner_id, course_id, raw in eval_rows:
        scores = {}
        numeric_scores = []
        
        # Parse Week 1-8 Scores
        for week in range(1, 9):
            # Regex 1: Strict Table format (e.g. | **Week 1** | **3)
            m1 = re.search(r'\|\s*\**(?:Week|w)\s*' + str(week) + r'\**\s*\|\s*\**([1-4])', raw, re.IGNORECASE)
            # Regex 2: Loose List format (e.g. Week 1 Score: 3)
            clean_raw = raw.replace('\n', ' ')
            m2 = re.search(r'Week\s*' + str(week) + r'.{0,40}?(?:Score|Sophistication).*?\b([1-4])\b', clean_raw, re.IGNORECASE)

            score_val = ""
            if m1:
                score_val = m1.group(1)
            elif m2:
                score_val = m2.group(1)
            
            scores[f"Week_{week}_Score"] = score_val
            if score_val:
                numeric_scores.append(int(score_val))
                
        # Calculate Peak and Mean Sophistication
        peak_soph = max(numeric_scores) if numeric_scores else 0
        mean_soph = sum(numeric_scores) / len(numeric_scores) if numeric_scores else 0
        
        # Parse Bloom Ceiling (Looking for L1 to L6)
        bloom_match = re.search(r'(?:Ceiling|Score).*?(L[1-6])', raw, re.IGNORECASE)
        bloom_score = bloom_match.group(1) if bloom_match else ""
        
        # Parse Narrative Synthesis
        synthesis_match = re.search(r'Synthesis(?:.*?)\n+(.*?)(?:###|---|\*\*\*)', raw, re.IGNORECASE | re.DOTALL)
        synthesis = synthesis_match.group(1).replace('\n', ' ').strip() if synthesis_match else ""
        
        # Format Raw Responses as JSON
        # Note: We align the first N answers with Week 1, 2...
        raw_ans_list = answers_map.get(learner_id, [])
        ans_json = json.dumps({f"Week {i+1}": ans for i, ans in enumerate(raw_ans_list)})

        row_dict = {
            "learner_id": learner_id,
            "course_id": course_id,
            "peak_bloom_score": bloom_score,
            "peak_sophistication": peak_soph,
            "mean_sophistication": round(mean_soph, 2),
            "overall_arc_summary": synthesis,
            "raw_responses_json": ans_json
        }
        row_dict.update(scores)
        clean_data.append(row_dict)
        
    conn.close()

    fields = ["learner_id", "course_id", "peak_bloom_score", "peak_sophistication", "mean_sophistication"] + \
             [f"Week_{i}_Score" for i in range(1, 9)] + ["overall_arc_summary", "raw_responses_json"]
    
    with open(CSV_OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(clean_data)

if __name__ == "__main__":
    export_clean()
    print("Clean matrix CSV exported to layer2_layer3_clean_matrix.csv")
