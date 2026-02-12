import json
import os
import time
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

# --- Configuration ---
INPUT_FILE = Path("data/output/recommendations_ab.json")
OUTPUT_FILE = Path("data/output/evaluation_results_gemini_scientific.json")
MODEL_NAME = "gemini-2.5-flash"

# Load API Key
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file")

client = genai.Client(api_key=API_KEY)

def generate_prompt(persona, recipe):
    """
    Constructs the prompt.
    """
    
    # 1. Format Nutrition
    nutri = recipe.get('nutrition', {})
    nutri_str = (
        f"Calories: {nutri.get('calories', 'N/A')} | "
        f"Protein: {nutri.get('protein', 'N/A')} | "
        f"Carbs: {nutri.get('carbs', 'N/A')} | "
        f"Fat: {nutri.get('fat', 'N/A')}"
    )

    # 2. Format Ingredients
    ingredients = recipe.get('ingredients', [])
    ing_str = ", ".join(ingredients) if isinstance(ingredients, list) else str(ingredients)

    # 3. Handle Empty Explanation (Control Group)
    explanation_text = recipe.get('explanation', "").strip()
    explanation_display = f'"{explanation_text}"' if explanation_text else "[NO EXPLANATION PROVIDED]"

    # 4. Construct the Full Prompt
    # We have two Roles:
    #    1. Scientific Reviewer:
    #       You are an impartial Scientific Reviewer specializing in Recommender Systems and Explainable AI.
    #    2. Nutritionist Evaluator:
    #       You are an impartial Nutritionist evaluator reviewing food recommendations for general healthy eating guidance.

    full_prompt = f"""
SYSTEM ROLE:
You are an impartial Scientific Reviewer specializing in Recommender Systems and Explainable AI.
Your job is to audit the quality of a food recommendation and its explanation using defined metrics.
Do not assume any information beyond what is provided.

TASK:
Please evaluate the following food recommendation against the User Profile.

--- USER PROFILE ---
Description: {persona['description']}
Goal: {persona['profile']['dietary_goal']}
Dietary Constraints: {json.dumps(persona['profile']['dietaryProfile'])}
Liked Ingredients: {", ".join(persona['profile']['likedIngredients'])}
Disliked Ingredients: {", ".join(persona['profile'].get('dislikedIngredients', []))}
Favorite Cuisines: {", ".join(persona['profile'].get('favoriteCuisines', []))}
--------------------

--- RECOMMENDATION ---
Item: {recipe['title']}
Nutrition: {nutri_str}
Ingredients: {ing_str}

Explanation Provided: {explanation_display}
----------------------

Score the following 3 metrics on a scale of 1 (Poor) to 5 (Excellent).

1. RELEVANCE (1-5):
   Is the meal appropriate and relevant for the user's specific goals and constraints? 

2. TRANSPARENCY (1-5):
   It aims to evaluate whether the explanations can reveal the internal working principles of the recommender models.

3. PERSUASIVENESS (1-5):
   It aims to evaluate “whether the explanations can increase the interaction probability of the users on the items.

Note: Some recommendations may not have an explanation.

Output strictly valid JSON with these keys:
{{
  "relevance_score": int,
  "transparency_score": int,
  "persuasiveness_score": int,
  "reasoning": "Short justification (1-2 sentences)"
}}
"""
    return full_prompt

def run_evaluation():
    if not INPUT_FILE.exists():
        print(f"Error: {INPUT_FILE} not found.")
        return

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    flat_results = {
        "evaluator_name": "Gemini-2.5-Flash (Scientific Reviewer)"
    }

    print(f"Starting Evaluation with {MODEL_NAME}...")
    
    for p_idx, entry in enumerate(data):
        persona = entry['persona']
        recommendations = entry['recommendations']
        
        print(f"\n--- Processing Persona {p_idx + 1} ---")

        for r_idx, recipe in enumerate(recommendations):
            print(f"   Evaluating Recipe {r_idx + 1}/{len(recommendations)}...", end="", flush=True)
            
            prompt = generate_prompt(persona, recipe)

            #print('0000000000 _ DUMMY Print 1 _ Prompt below _ 0000000000')
            #print(prompt)
            #input("Press Enter to continue...")

            try:
                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json" 
                    )
                )
                
                result = json.loads(response.text)

                #print('0000000000 _ DUMMY Print 2 _ Response below _ 0000000000')
                #print(response.text)
                #input("Press Enter to continue...")

                # 1-based indexing for keys
                key_prefix = f"p{p_idx + 1}_r{r_idx + 1}"
                
                flat_results[f"{key_prefix}_rel"] = str(result.get('relevance_score', 0))
                flat_results[f"{key_prefix}_trans"] = str(result.get('transparency_score', 0))
                flat_results[f"{key_prefix}_pers"] = str(result.get('persuasiveness_score', 0))
                
                print(" Done.")
                time.sleep(1) 

            except Exception as e:
                print(f" Error: {e}")
                key_prefix = f"p{p_idx + 1}_r{r_idx + 1}"
                flat_results[f"{key_prefix}_rel"] = "0"
                flat_results[f"{key_prefix}_trans"] = "0"
                flat_results[f"{key_prefix}_pers"] = "0"

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(flat_results, f, indent=2)

    print(f"\n✅ Evaluation Complete. Results saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    run_evaluation()