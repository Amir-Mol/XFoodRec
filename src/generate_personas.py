import os
import json
import random
from typing import List, Dict
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Configuration
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "output"
OUTPUT_FILE = OUTPUT_DIR / "personas.json"
NUM_PERSONAS = 10

# Initialize client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_diverse_personas(n: int = 10) -> List[Dict]:
    """
    Generates synthetic user profiles using GPT-4o.
    Each profile represents a diverse case in dietary needs.
    """
    
    system_prompt = (
        "You are a User Research Specialist for a food AI application. "
        "Generate realistic user profiles (personas) that represent extreme and "
        "diverse edge cases in dietary needs."
    )

    user_prompt = f"""
    Create {n} distinct user profiles for a food recommendation app.
    
    CRITICAL INSTRUCTIONS:
    1. **Diversity**: Maximize differences between users. Include rare combinations 
       (e.g., "Vegan Bodybuilder", "Diabetic with Nut Allergy", "Student with Low Budget").
    2. **Goals**: Assign a specific 'dietary_goal' from this list: 
       ['Weight Loss', 'Muscle Gain', 'Maintenance', 'Medical Management', 'Energy Boost'].
    3. **Constraints**: Ensure varying levels of allergies and dislikes.
    4.  activityLevel should be one of the following: sedentary, lightly_active, moderately_active, very_active

    Output a JSON object with a key 'personas' containing a list of {n} objects. 
    Each object must strictly follow this schema:
    
    {{
        "id": "user_01",
        "description": "Short summary (e.g., 'A busy vegan lawyer trying to gain muscle.')",
        "profile": {{
            "age": 30,
            "gender": "Female",
            "height": 165.0,  # cm
            "weight": 60.0,   # kg
            "activityLevel": "Active",
            "dietary_goal": "Muscle Gain",
            "dietaryProfile": {{
                "dietaryRestrictions": {{ "selected": ["Vegan"], "other": "" }},
                "foodAllergies": {{ "selected": ["Peanuts"], "other": "" }},
                "healthConditions": {{ "selected": [], "other": "" }}
            }},
            "likedIngredients": ["Tofu", "Quinoa"],
            "dislikedIngredients": ["Mushrooms"],
            "favoriteCuisines": ["Asian"]
        }}
    }}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-5.2",  # or gpt-4o or gpt-5.2-mini
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.8,  # High temperature for creativity/diversity
        )
        
        content = response.choices[0].message.content
        data = json.loads(content)
        return data.get("personas", [])

    except Exception as e:
        print(f"Error generating personas: {e}")
        return []

def save_personas(personas: List[Dict]):
    """Saves the generated personas to a JSON file."""
    # Ensure directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(personas, f, indent=4)
    
    print(f"Successfully saved {len(personas)} personas to {OUTPUT_FILE}")

def main():
    print(f"Generating {NUM_PERSONAS} synthetic personas...")
    personas = generate_diverse_personas(NUM_PERSONAS)
    
    if personas:
        save_personas(personas)
        # Print a preview of the first persona to verify
        print("\nPreview of first persona:")
        print(json.dumps(personas[0], indent=2))
    else:
        print("Failed to generate personas.")

if __name__ == "__main__":
    main()