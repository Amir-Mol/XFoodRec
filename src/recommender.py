import json
import numpy as np
import pandas as pd
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI

from config import (
    RECIPES_FILE, 
    PERSONAS_FILE, 
    RECOMMENDATIONS_FILE,
    EMBEDDING_MODEL_NAME, 
    LLM_MODEL_NAME,
    CONSIDERATION_SET_SIZE,
    FINAL_K
)

class XFoodRecommender:
    def __init__(self):
        """
        Initializes the Hybrid Recommender Engine.
        """
        print(f"Loading embedding model: {EMBEDDING_MODEL_NAME}...")
        self.encoder = SentenceTransformer(EMBEDDING_MODEL_NAME)
        
        print(f"Loading recipe data from {RECIPES_FILE}...")
        try:
            self.recipes_df = pd.read_parquet(RECIPES_FILE)

            # To ensure ID is always a string
            self.recipes_df['recipe_id'] = self.recipes_df['recipe_id'].astype(str)

            print("Generating recipe embeddings (Title + Ingredients + Tags)...")
            
            def create_recipe_doc(row):
                # Combine critical fields into one string for the Vector Engine
                return (
                    f"Title: {row['title']}. "
                    f"Ingredients: {row.get('ingredients_title', row['ingredients'])}. "
                    f"Tags: {row.get('tags', '')}. "
                    f"Calories: {row.get('calories_per_serving [cal]', '')}."
                )
            
            # Create a temporary column for embedding
            self.recipes_df['semantic_doc'] = self.recipes_df.apply(create_recipe_doc, axis=1)
            
            self.recipe_embeddings = self.encoder.encode(
                self.recipes_df['semantic_doc'].tolist(), 
                show_progress_bar=True,
                convert_to_numpy=True
            )
        except FileNotFoundError:
            raise FileNotFoundError(f"Could not find {RECIPES_FILE}.")

        self.client = OpenAI()

    def _create_user_vector_query(self, profile: Dict) -> np.ndarray:
        """
        Includes Goal, Cuisines, Likes, and Health Conditions for semantic matching.
        """
        goal = profile.get("dietary_goal", "Maintenance")
        likes = ", ".join(profile.get("likedIngredients", []))
        cuisines = ", ".join(profile.get("favoriteCuisines", []))     
        # We add conditions here so the vector search favors "diabetic-friendly" recipes naturally, even before the hard filter.
        conditions = ", ".join(profile['dietaryProfile']['healthConditions']['selected'])
        activity = profile.get("activityLevel", "Moderate")

        text_query = (
            f"User goal: {goal}. "
            f"Dietary conditions: {conditions}. "
            f"Activity Level: {activity}. "
            f"Preferences: {likes}. "
            f"Cuisine style: {cuisines}."
        )
        return self.encoder.encode(text_query).reshape(1, -1)

    def _apply_hard_constraints(self, df: pd.DataFrame, profile: Dict) -> pd.DataFrame:
        """
        Strict Hard Constraints
        """
        filtered_df = df.copy()        
        diet_profile = profile['dietaryProfile']
        
        # 1. Allergy Filter
        allergies = [a.lower() for a in diet_profile['foodAllergies']['selected']]
        if allergies:
            # Function to check if ANY allergy word appears in the ingredients string
            def contains_allergen(ing_str):
                ing_lower = str(ing_str).lower()
                for allergen in allergies:
                    if allergen in ing_lower:
                        return True
                return False
            
            # Keep rows that do NOT contain allergens
            filtered_df = filtered_df[~filtered_df['ingredients'].apply(contains_allergen)]

        # 2. Dietary Restrictions (e.g., Vegan, Vegetarian)
        restrictions = [r.lower() for r in diet_profile['dietaryRestrictions']['selected']]
        
        # Map user restrictions to dataset tags (simple mapping logic)
        for restriction in restrictions:
            if 'vegan' in restriction:
                # Filter rows where 'tags' column contains 'vegan' (case insensitive)
                filtered_df = filtered_df[filtered_df['tags'].astype(str).str.lower().str.contains('vegan')]
            elif 'vegetarian' in restriction:
                filtered_df = filtered_df[filtered_df['tags'].astype(str).str.lower().str.contains('vegetarian')]
            elif 'gluten' in restriction:
                 # Check tags OR ingredients
                 filtered_df = filtered_df[
                     filtered_df['tags'].astype(str).str.lower().str.contains('gluten') |
                     ~filtered_df['ingredients'].astype(str).str.lower().str.contains('flour|wheat|bread') 
                 ]

        return filtered_df

    def stage_1_retrieval(self, user_profile: Dict) -> pd.DataFrame:
        """
        Hybrid Retrieval: Hard Filters -> Vector Search
        """
        # 1. Apply Hard Constraints FIRST (Safety First)
        safe_recipes = self._apply_hard_constraints(self.recipes_df, user_profile)
        
        if safe_recipes.empty:
            print("Warning: Hard constraints removed all recipes. Relaxing filters...")
            

        # 2. Vector Search on remaining candidates
        safe_indices = safe_recipes.index
        safe_embeddings = self.recipe_embeddings[safe_indices]
        
        user_vec = self._create_user_vector_query(user_profile)
        similarities = cosine_similarity(user_vec, safe_embeddings)[0]
        
        # 3. Rank
        safe_recipes = safe_recipes.copy()
        safe_recipes['similarity_score'] = similarities
        
        return safe_recipes.nlargest(CONSIDERATION_SET_SIZE, 'similarity_score')

    def stage_2_ranking_and_explanation(self, user_profile: Dict, candidates: pd.DataFrame) -> List[Dict]:
        """
        Stage 2: CoT Reasoning with Rich Candidate Data
        """
        # Passing nutritional data allows the LLM to reason about "Muscle Gain" (Protein) or "Weight Loss" (Calories)
        candidates_json = candidates[[
            'recipe_id', 'title', 'ingredients_title', 
            'calories_per_serving [cal]', 
            'protein_per_serving [g]', 
            'totalcarbohydrate_per_serving [g]', 
            'totalfat_per_serving [g]', 
            'tags'
        ]].to_dict(orient='records')

        for rec in candidates_json:
            for key, val in rec.items():
                if isinstance(val, np.ndarray):
                    rec[key] = val.tolist()
              
        system_prompt = (
            "You are an AI-powered food recommendation assistant. "
            "You will receive a list of candidate recipes that has already been filtered by a hard-constraint "
            "('Never List') module to remove items that violate the user's dietary restrictions and allergies.\n\n"
        
            "Your task is to rank the remaining candidates and return the TOP 6 recipes, balancing two goals:\n"
            "(A) match the user's profile (goal + tastes) and\n"
            "(B) gently prefer healthier options when it does not significantly reduce profile match.\n\n"
        
            "IMPORTANT RULES:\n"
            "- Do NOT reveal internal reasoning steps.\n"
            "- Base explanations only on the provided user profile and recipe metadata.\n"
            "- Do not invent nutrition facts or health claims that are not supported by the provided data.\n"
            "- Do not provide medical advice.\n\n"
        
            "INTERNAL RANKING PRINCIPLES (apply silently):\n"
            "1. PRIMARY: PROFILE FIT. Prioritize recipes that best match the user's goal and preferences "
            "(liked ingredients/cuisines, avoid disliked ingredients, dietaryProfile (dietaryRestrictions, foodAllergies, healthConditions)).\n"
            "2. SECONDARY: HEALTHIER BIAS. When two recipes are similarly good for the user, rank the healthier-leaning one higher "
            "(e.g., more nutrient-dense, more balanced macros, less excessive sugar/sodium/saturated fat—based only on provided data).\n"
        
            "EXPLANATION REQUIREMENTS (user-visible):\n"
            "- TRANSPARENCY: Explicitly cite at least one user factor that drove the choice (goal or preference). This Transparency aims to evaluate “whether the explanations can reveal the internal working principles of the recommender models\n"
            "- HEALTH JUSTIFICATION: If the recipe is a healthier-leaning pick (or chosen over a similar option), briefly mention the relevant nutrition cue "
            "(e.g., 'higher protein', 'more balanced meal', 'includes vegetables/whole grains', 'lower added sugar') without overstating.\n"
            "- PERSUASIVENESS: Use motivating, non-clinical language that encourages trying the recipe. This Persuasiveness aims to evaluate “whether the explanations can increase the interaction probability of the users on the items.\n"
            "- Keep each explanation short (3–4 sentences).\n\n"
        
            "Output strictly valid JSON in this format:\n"
            "{ 'recommendations': [ { 'recipe_id': '...', 'explanation': '...' } ] }"
        )

        user_prompt = f"""
        User Profile: {json.dumps(user_profile, indent=2)}       
        Candidates: {json.dumps(candidates_json, indent=2)}
        """  

        response = self.client.chat.completions.create(
            model=LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.5
        )

        try:
            content = response.choices[0].message.content
            result = json.loads(content)
                         
            final_recs = []
            for rec in result.get('recommendations', []):
                llm_id = str(rec['recipe_id'])
                # Find the original title
                original_row = candidates[candidates['recipe_id'].astype(str) == llm_id]

                if not original_row.empty:
                    row_data = original_row.iloc[0]
                    ingredients = row_data.get('ingredients_title', [])
                    
                    if isinstance(ingredients, np.ndarray):
                        ingredients = ingredients.tolist()

                    final_recs.append({
                        "recipe_id": llm_id,
                        "title": row_data['title'],
                        "explanation": rec['explanation'],
                        "ingredients": ingredients,
                        "nutrition": {
                            "calories": float(row_data.get('calories_per_serving [cal]', 0)),
                            "protein": f"{row_data.get('protein_per_serving [g]', 0)}g",
                            "carbs": f"{row_data.get('totalcarbohydrate_per_serving [g]', 0)}g",
                            "fat": f"{row_data.get('totalfat_per_serving [g]', 0)}g"
                        }                       
                    })

                else:
                    print(f"⚠️ Warning: LLM returned unknown ID {llm_id}. Skipping.")

            return final_recs
            
        except Exception as e:
            print(f"Error in Stage 2: {e}")
            return []

    def run_batch(self, personas: List[Dict]):
        all_results = []
        for i, persona in enumerate(personas):

            print(f"\nProcessing Persona {i+1}/{len(personas)}: {persona['id']} ({persona['profile']['dietary_goal']})")

            candidates = self.stage_1_retrieval(persona['profile'])
            print(f"  Stage 1: Retrieved {len(candidates)} candidates.")
            
            recommendations = self.stage_2_ranking_and_explanation(persona['profile'], candidates)
            print(f"  Stage 2: Generated {len(recommendations)} final recommendations.")
            
            all_results.append({
                "persona": persona,
                "recommendations": recommendations
            })

        with open(RECOMMENDATIONS_FILE, 'w') as f:
            json.dump(all_results, f, indent=2)
        print(f"\nSaved full results to {RECOMMENDATIONS_FILE}")

def main():
    if not PERSONAS_FILE.exists():
        print("Please run Step 1 (Persona Generator) first.")
        return
        
    with open(PERSONAS_FILE, 'r') as f:
        personas = json.load(f)

    engine = XFoodRecommender()
    engine.run_batch(personas)

if __name__ == "__main__":
    main()