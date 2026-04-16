import json
import os

remaining_path = 'other_candidates_for_review.md'

with open('negative_candidates.json', 'r') as f:
    candidates = json.load(f)

flagged_learners = {160, 62, 162, 64, 17, 10, 120, 195, 34, 216, 125, 147, 135, 73, 58, 21, 202, 124}

with open(remaining_path, 'w') as f:
    f.write("# Other Flagged Responses for Review\n\n")
    f.write("These responses were caught by the negative keyword filter but were excluded from the main analysis as they were either about personal struggles (not the course/AI itself), false positives, or simply used the word in a different context.\n\n")
    
    count = 0
    for cand in candidates:
        if cand['learner_id'] not in flagged_learners:
            count += 1
            f.write(f"### Learner {cand['learner_id']} (Course {cand['course_id']})\n")
            f.write(f"> {cand['answer']}\n\n")
    
    print(f"Exported {count} other candidates.")
