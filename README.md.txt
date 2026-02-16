# XFoodRec: A Hybrid Explainable Food Recommendation Framework

**Related Project:** This repository contains the algorithm and evaluation framework for NutriRecom Mobile Application which can be found here [https://github.com/Amir-Mol/ai-food-frontend]:

## Overview
In this project, we address the challenge of **Explainability** in food recommender systems. Unlike traditional "black-box" recommenders that simply output a list of items, XFoodRec generates personalized, natural language explanations alongside every recommendation.

We introduce a novel A/B Testing Framework to rigorously measure the impact of these explanations on user trust and persuasiveness. To avoid the high cost and bias of traditional evaluation, we utilize a Synthetic Persona Generation pipeline and an Automated LLM Judge acting as a scientific reviewer.


## Repository Structure
XFoodRec/
├── data/  
│   ├── input/          # Contains the source recipe dataset (recipes.parquet)  
│   └── output/         # Generated personas, recommendations, and evaluation results  
├── src/  
│   ├── generate_personas.py  # Step 1: Creates synthetic user profiles  
│   ├── recommender.py        # Step 2: Hybrid Retrieval + LLM Reranking & Explanation  
│   ├── create_ab_test.py     # Step 3: Randomly removes explanations for the Control Group  
│   └── evaluator.py          # Step 4: Automated scoring using Google Gemini  
└── requirements.txt    # Python dependencies


## 🛠️ Methodology & System Architecture

Our system follows a four-stage pipeline designed to ensure scientific rigor and reproducibility.

### 1. Synthetic Persona Generation
We used LLM (GPT-5.2) to generate diverse and realistic user personas, With this prompt:

    System Prompt:  
    You are a User Research Specialist for a food AI application.
    Generate realistic user profiles (personas) that represent extreme and 
    diverse edge cases in dietary needs.

    User Prompt:  
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


### 2. Hybrid Recommendation Engine
We utilized a **Retrieve-Then-Rerank** architecture:
1.  **Retrieval:** We used TF-IDF vectorization on ingredient lists to retrieve the top 100 candidate recipes based on content similarity.
2.  **Reranking & Explanation:** We employed an LLM (GPT-4o) to select the best 6 items and generate explanations. With the following prompt:

    
        System Prompt:
        You are an AI-powered food recommendation assistant. 
        You will receive a list of candidate recipes that has already been filtered by a hard-constraint 
        ('Never List') module to remove items that violate the user's dietary restrictions and allergies.

        Your task is to rank the remaining candidates and return the TOP 6 recipes, balancing two goals:
        (A) match the user's profile (goal + tastes) and
        (B) gently prefer healthier options when it does not significantly reduce profile match.

        IMPORTANT RULES:
        - Do NOT reveal internal reasoning steps.
        - Base explanations only on the provided user profile and recipe metadata.
        - Do not invent nutrition facts or health claims that are not supported by the provided data.
        - Do not provide medical advice.

        INTERNAL RANKING PRINCIPLES (apply silently):
        1. PRIMARY: PROFILE FIT. Prioritize recipes that best match the user's goal and preferences 
        (liked ingredients/cuisines, avoid disliked ingredients, dietaryProfile (dietaryRestrictions, foodAllergies, healthConditions)).
        2. SECONDARY: HEALTHIER BIAS. When two recipes are similarly good for the user, rank the healthier-leaning one higher
        (e.g., more nutrient-dense, more balanced macros, less excessive sugar/sodium/saturated fat—based only on provided data).

        EXPLANATION REQUIREMENTS (user-visible):
        - TRANSPARENCY: Explicitly cite at least one user factor that drove the choice (goal or preference). This Transparency aims to evaluate “whether the explanations can reveal the internal working principles of the recommender models
        - HEALTH JUSTIFICATION: If the recipe is a healthier-leaning pick (or chosen over a similar option), briefly mention the relevant nutrition cue
        (e.g., 'higher protein', 'more balanced meal', 'includes vegetables/whole grains', 'lower added sugar') without overstating.
        - PERSUASIVENESS: Use motivating, non-clinical language that encourages trying the recipe. This Persuasiveness aims to evaluate “whether the explanations can increase the interaction probability of the users on the items.
        - Keep each explanation short (3–4 sentences).

        Output strictly valid JSON in this format:
        { 'recommendations': [ { 'recipe_id': '...', 'explanation': '...' } ] }"

        User Prompt:
        User Profile      
        List of Candidates REcipes
    

### 3. A/B Testing (Ablation Study)
To measure the true impact of the AI explanations, we implement a Within-Subjects Design:
* **Group B (Treatment):** Users see the recommendation with the AI explanation.
* **Group A (Control):** Users see the exact same recommendation, but the explanation is removed.
* **Implementation:** The script `src/create_ab_test.py` randomly masks 50% of the explanations before evaluation.


### 4. Automated Evaluation (The "LLM Judge")
To avoid self-preference bias (using GPT to evaluate GPT), we utilize **Google Gemini 2.5 Flash** with two different roles: 1. An impartial scientific reviewer, 2. A Nutritionist. The following prompt is for the scientific reviewer role:

    Prompt:  
    SYSTEM ROLE:
    You are an impartial Scientific Reviewer specializing in Recommender Systems and Explainable AI.  
    Your job is to audit the quality of a food recommendation and its explanation using defined metrics.  
    Do not assume any information beyond what is provided.  


    TASK:  
    Please evaluate the following food recommendation against the User Profile.  


    USER PROFILE:  
    Description  
    Goal  
    Dietary Constraints  
    Liked Ingredients  
    Disliked Ingredients  
    Favorite Cuisines  
      


    RECOMMENDATION:  
    Item  
    Nutrition  
    Ingredients  


    Explanation   
      


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



## Installation & Usage

### 1. Setup Environment
```bash
git clone https://github.com/Amir-Mol/XFoodRec.git
cd XFoodRec
python -m venv xfood_env
# Windows
.\xfood_env\Scripts\activate
# Mac/Linux
source xfood_env/bin/activate

pip install -r requirements.txt
```

### 2. Configure API Keys
The project requires API keys for OpenAI and Google Gemini.
Rename the example file .env.example to .env and put your API key there.


### 3. Run the Pipeline
Execute the scripts in this specific order to reproduce the experiment:

```Bash
# 1. Generate Personas
python src/generate_personas.py

# 2. Generate Recommendations +Explanations
python src/recommender.py

# 3. Create A/B Test Dataset (Splits into Treatment/Control)
python src/create_ab_test.py

# 4. Run Automated Evaluation (Gemini Judge)
python src/evaluator.py
```
The evaluation results will be saved in data/output/ directory as a JSON file. You can use json_to_csv.py to convert it into a csv file.  

## Citation
If you use this code or methodology, please cite our paper:
[WILL BE COMPLETED: XFoodRec Paper, SIGIR 2026]