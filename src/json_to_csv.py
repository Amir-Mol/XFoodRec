import json
import csv
import pandas as pd
from pathlib import Path

# --- Configuration ---
# 1. The Source of Truth (Metadata, Groups A/B)
METADATA_FILE = Path("data/output/recommendations_ab.json")

# 2. The Scores (LLM or Human)
SCORE_FILES = [
    Path("data/output/evaluation_results_gemini_scientific.json"),
    Path("data/output/evaluation_results_gemini_nutritionist.json"),
    # Path("data/output/evaluation_human_alice.json"), 
]

OUTPUT_CSV = Path("data/output/analysis_dataset.csv")

def convert_to_csv():
    if not METADATA_FILE.exists():
        print(f" Error: Metadata file {METADATA_FILE} not found.")
        return

    # 1. Load Metadata (The Reference)
    with open(METADATA_FILE, 'r', encoding='utf-8') as f:
        metadata = json.load(f)

    # Prepare CSV Data List
    csv_rows = []

    # 2. Loop through each Score File (LLM or Human)
    for score_path in SCORE_FILES:
        if not score_path.exists():
            print(f" Warning: Score file {score_path} not found. Skipping.")
            continue
            
        print(f"Processing scores from: {score_path.name}...")
        with open(score_path, 'r', encoding='utf-8') as f:
            scores = json.load(f)

        evaluator_name = scores.get("evaluator_name", score_path.stem)

        # 3. Merge Metadata + Scores
        for p_idx, entry in enumerate(metadata):
            persona_id = p_idx + 1
            # Simplify persona description for CSV (optional)
            persona_goal = entry['persona']['profile']['dietary_goal']

            for r_idx, recipe in enumerate(entry['recommendations']):
                recipe_idx = r_idx + 1
                
                # --- KEY: Match pX_rY ---
                key_prefix = f"p{persona_id}_r{recipe_idx}"
                
                # Get Scores (Default to Empty if missing)
                rel = scores.get(f"{key_prefix}_rel", "")
                trans = scores.get(f"{key_prefix}_trans", "")
                pers = scores.get(f"{key_prefix}_pers", "")

                # Skip if this evaluator didn't grade this item
                if not rel: 
                    continue

                # Get Experimental Group (The most important part!)
                # 'group' key exists in recommendations_ab.json
                group_status = recipe.get("group", "Unknown") 
                
                # Clean up Group Name for SPSS (Optional)
                # "B_Treatment" -> "Treatment", "A_Control" -> "Control"
                group_clean = group_status.split('_')[-1] if '_' in group_status else group_status

                row = {
                    "Evaluator": evaluator_name,
                    "Persona_ID": persona_id,
                    "Persona_Goal": persona_goal,
                    "Recipe_Order": recipe_idx,
                    "Recipe_ID_Original": recipe['recipe_id'],
                    "Group": group_clean,  # Treatment vs Control
                    "Relevance": rel,
                    "Transparency": trans,
                    "Persuasiveness": pers
                }
                csv_rows.append(row)

    # 4. Save to CSV
    if csv_rows:
        df = pd.DataFrame(csv_rows)
        df.to_csv(OUTPUT_CSV, index=False)
        print(f"\n Success! CSV saved to: {OUTPUT_CSV}")
        print(f"   Total Data Points: {len(df)}")
        print("\n   Preview:")
        print(df.head())
    else:
        print("\n No data rows were generated.")

if __name__ == "__main__":
    convert_to_csv()