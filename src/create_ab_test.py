import json
import random
from pathlib import Path

# Configuration
INPUT_FILE = Path("data/output/recommendations.json")
OUTPUT_FILE = Path("data/output/recommendations_ab.json")

def create_ab_dataset():
    if not INPUT_FILE.exists():
        print(f"Error: {INPUT_FILE} not found. Run Recommender first.")
        return

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Processing {len(data)} personas for A/B testing...")

    for entry in data:
        recs = entry['recommendations']
        
        # We have 6 recs. We want exactly 3 to be Control (No Explanation)
        # Create a list of indices [0, 1, 2, 3, 4, 5]
        indices = list(range(len(recs)))
        
        # Randomly select 3 indices to be the "Control" group
        control_indices = random.sample(indices, k=3)
        
        for i in indices:
            # Tag the data so we know later which group it belonged to
            if i in control_indices:
                recs[i]['group'] = 'A_Control'
                recs[i]['original_explanation'] = recs[i]['explanation'] # Backup just in case
                recs[i]['explanation'] = "" # Remove for the test
            else:
                recs[i]['group'] = 'B_Treatment'
                # Explanation remains touched

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    print(f"✅ A/B Dataset created: {OUTPUT_FILE}")
    print("   - Each persona has 3 Control (No Expl) and 3 Treatment (With Expl) items.")
    print("   - Use this file for the Evaluator and HTML Tool.")

if __name__ == "__main__":
    # Optional: Set seed for reproducibility if you want the same split every time
    # random.seed(42) 
    create_ab_dataset()