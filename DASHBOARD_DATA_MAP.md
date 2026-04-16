# Learner Progression Dashboard: Data Architecture Walkthrough

This document explains the "Source-to-Screen" journey of the data displayed in your interactive dashboard. It outlines the raw origins in the SQLite database, the AI processing pipelines, and how they are synthesized into the visual progression metrics.

## 1. Data Mode: Usage Reflections
Categorized as **"Layered Qualitative Analysis,"** this mode tracks the weekly journey of learners via their usage diaries.

### Data Origin & Flow
1.  **Raw Input**: SQLite `responses` table where `quiz_type` is `usage_reflection`.
2.  **AI Pipeline (`process_reflections.py`)**: 
    -   Uses local **Gemma 4:e4B** (via Ollama).
    -   Processes chronological weekly answers into a single "Narrative Arc."
3.  **Scoring Framework**:
    -   **Sophistication Score (1-4)**: Extracted per week based on tool integration level.
    -   **Bloom Ceiling (L1-L6)**: Identifies the highest cognitive level reached during the course.
4.  **Backend Storage**: Results are saved to the `learner_arcs` table in `bootcamp.db`.
5.  **Dashboard Export**: `export_clean_csv.py` parses the LLM's unstructured text into `layer2_layer3_clean_matrix.csv`.

---

## 2. Data Mode: Milestone Progression
Categorized as **"Comparative Transformation Analysis,"** this mode measures the "Pre vs. Post" delta for the entire bootcamp.

### Data Origin & Flow
1.  **Raw Input**: SQLite `responses` table where `quiz_type` is either `milestone_baseline_profile` (Day 1) or `milestone_outcomes_profile` (Final Day).
2.  **AI Pipeline (`process_milestones.py`)**:
    -   Uses **Gemini 2.5 Flash API** for high-speed batch processing.
    -   Compares the start and end responses for the same learner.
3.  **Metrics Calculated**:
    -   **Baseline Sophistication/Bloom**: Capability on Day 1.
    -   **Outcomes Sophistication/Bloom**: Capability on the Final Day.
    -   **Improvement Delta**: The mathematical shift between the two states.
4.  **Backend Storage**: Saved to the `milestone_arcs` table in `bootcamp.db`.
5.  **Dashboard Export**: Directly exported to `milestone_matrix.csv`.

---

## 3. Scoring Frameworks Explained

The dashboard maps all qualitative text against the following two proprietary frameworks:

### Layer 2: Sophistication Rubric (Scale 1–4)
Focuses on how deeply AI is integrated into the learner's workflow.
- **1 (Casual/Ad-hoc)**: Scattered use for low-stakes search/writing.
- **2 (Episodic)**: Intentional use for discrete projects/tasks.
- **3 (Integrated)**: Repeated use of custom prompts/tools as a thinking partner.
- **4 (Systemic)**: Use of AI to build or redesign entire organizational workflows.

### Layer 3: Bloom’s Taxonomy Ceiling (L1–L6)
Focuses on the cognitive "peak" of the learner's AI interactions.
- **L1 (Remember)**: Basic recall of AI tool names.
- **L2 (Understand)**: Explaining how LLMs work.
- **L3 (Apply)**: Using prompts to complete specific jobs.
- **L4 (Analyze)**: Breaking down complex problems with AI.
- **L5 (Evaluate)**: Critical assessment of AI outputs for bias/logic.
- **L6 (Create)**: Building new systems or original AI artifacts.

---

## 4. How to Update the Data
If you add new cohort data to the `responses` table, follow these steps to refresh the UI:

1.  **To Refresh Reflections**: 
    ```bash
    python3 process_reflections.py
    python3 export_clean_csv.py
    ```
2.  **To Refresh Milestones**:
    ```bash
    export GEMINI_API_KEY="your_api_key"
    python3 process_milestones.py
    ```
    *(The milestone script automatically handles the CSV export).*

---

> [!TIP]
> **Data Integrity Check**: 
> You can verify any AI evaluation by clicking a learner in the "Learner Directory" and scrolling to the bottom of the Narrative panel. The **"Raw Responses"** section allows you to compare the original human text against the AI's final scorecard.
