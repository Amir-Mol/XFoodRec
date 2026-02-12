import json
from pathlib import Path

# Configuration
INPUT_FILE = Path("data/output/recommendations_ab.json") 
RESULTS_FILE = Path("data/output/evaluation_results.json")
OUTPUT_FILE = Path("data/output/human_evaluation_tool.html")

def generate_html_report():
    if not INPUT_FILE.exists():
        print(f"Error: {INPUT_FILE} not found. Please run src/create_ab_test.py first.")
        return

    # 1. Load Recommendations
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 2. Check for Pre-filled Results
    preloaded_json = "{}"
    if RESULTS_FILE.exists():
        try:
            with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
                preloaded_json = f.read()
        except:
            pass

    # --- HTML Header ---
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>XFoodRec Human Evaluation</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { background-color: #f4f6f9; font-family: 'Segoe UI', sans-serif; padding-bottom: 100px; }
            
            /* Persona Column */
            .persona-card { 
                position: sticky; top: 20px; 
                background: white; padding: 20px; border-radius: 12px; 
                box-shadow: 0 4px 12px rgba(0,0,0,0.05); border-left: 5px solid #0d6efd;
                height: fit-content; max-height: 90vh; overflow-y: auto;
            }
            
            /* Recipe Card */
            .recipe-card { border: none; margin-bottom: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); background: white; }
            .recipe-header { background-color: #fff; padding: 15px 20px; border-bottom: 1px solid #f0f0f0; border-radius: 12px 12px 0 0; }
            .recipe-body { padding: 20px; }
            
            /* Data Badges */
            .nutri-badge { font-size: 0.85em; background: #eef2ff; color: #4f46e5; padding: 4px 8px; border-radius: 6px; margin-right: 5px; font-weight: 600; }
            .ing-list { font-size: 0.9em; color: #666; margin-bottom: 15px; font-style: italic; }
            
            /* Explanation Boxes */
            .explanation-box { 
                background-color: #f0fdf4; border-left: 4px solid #16a34a; 
                padding: 15px; border-radius: 4px; margin-bottom: 20px; 
                color: #166534; font-size: 0.95rem;
            }
            .no-expl-box {
                background-color: #f8f9fa; border: 1px dashed #ced4da;
                padding: 15px; border-radius: 4px; margin-bottom: 20px;
                color: #6c757d; font-style: italic; text-align: center;
            }
            
            /* Evaluation Inputs */
            .eval-row { background: #fafafa; padding: 15px; border-radius: 8px; border: 1px dashed #ddd; transition: background-color 0.3s; }
            .form-label { font-size: 0.85rem; font-weight: bold; color: #555; margin-bottom: 2px; }
            
            /* Visual Feedback for Completed Scores */
            select.eval-input.filled {
                background-color: #d1e7dd; /* Light Green */
                border-color: #198754;
                color: #0f5132;
                font-weight: bold;
            }

            /* Sticky Footer */
            .sticky-footer {
                position: fixed; bottom: 0; left: 0; right: 0;
                background: white; padding: 15px;
                box-shadow: 0 -4px 20px rgba(0,0,0,0.1);
                z-index: 1000; display: flex; justify-content: space-between; align-items: center;
            }
            
            #fileInput { display: none; }
            
            .instruction-box { background: #fff; padding: 20px; border-radius: 8px; border: 1px solid #e0e0e0; margin-bottom: 30px; }
        </style>
    </head>
    <body>
        <div class="container-fluid px-4 py-4">
            <h2 class="text-center mb-4">XFoodRec Evaluation Dashboard</h2>
            
            <div class="row justify-content-center mb-4">
                <div class="col-md-6">
                    <div class="input-group">
                        <span class="input-group-text bg-primary text-white">Evaluator Name:</span>
                        <input type="text" class="form-control eval-input" data-key="evaluator_name" placeholder="Enter your name here..." required>
                    </div>
                </div>
            </div>

            <div class="instruction-box">
                <h5>📋 Instructions for Evaluators</h5>
                <p>Please review the <strong>User Persona</strong> on the left (10 personas), then rate the 6 recommendations (for each persona) on the right based on these criteria:</p>
                <ul>
                    <li><strong>Relevance (1-5):</strong> Is the meal appropriate and relevant for the user's specific goals and constraints?</li>
                    <li><strong>Transparency (1-5):</strong> It aims to evaluate “whether the explanations can reveal the internal working principles of the recommender models.</li>
                    <li><strong>Persuasiveness (1-5):</strong> It aims to evaluate “whether the explanations can increase the interaction probability of the users on the items.</li>
                </ul>
                <p class="mb-0 text-muted small">
                    <strong>Note:</strong> Some recommendations may not have an explanation.
                    <br>                
                    <strong>How to Submit:</strong>  
                    When finished, click <strong>"Save & Export JSON"</strong>, It downloads a JSON file. Email the file to the researcher.
                </p>
            </div>
    """

    # --- Loop through Personas ---
    for p_idx, entry in enumerate(data):
        persona = entry['persona']
        profile = persona['profile']
        recs = entry['recommendations']

        allergies = ", ".join(profile['dietaryProfile']['foodAllergies']['selected']) or "None"
        conditions = ", ".join(profile['dietaryProfile']['healthConditions']['selected'])
        
        html_content += f"""
        <div class="row mb-5 border-bottom pb-5">
            <div class="col-md-3">
                <div class="persona-card">
                    <h5 class="text-primary">Persona {p_idx + 1}</h5>
                    <p class="small text-muted">{persona['description']}</p>
                    <hr>
                    <div class="mb-3">
                        <span class="badge bg-danger mb-1">Goal: {profile['dietary_goal']}</span>
                        <span class="badge bg-warning text-dark mb-1">Allergies: {allergies}</span>
                    </div>
                    <p class="small"><strong>Conditions:</strong> {conditions}</p>
                    <p class="small"><strong>Likes:</strong> {", ".join(profile['likedIngredients'])}</p>
                    <p class="small"><strong>Dislikes:</strong> {", ".join(profile['dislikedIngredients'])}</p>
                </div>
            </div>

            <div class="col-md-9">
        """

        if not recs:
            html_content += """<div class="alert alert-warning">No recommendations found.</div>"""
        
        for r_idx, rec in enumerate(recs):
            nutri = rec.get('nutrition', {})
            ingredients_list = ", ".join(rec.get('ingredients', [])) if isinstance(rec.get('ingredients'), list) else str(rec.get('ingredients', ''))

            # --- A/B LOGIC ---
            if rec.get('explanation') and rec['explanation'].strip() != "":
                expl_html = f"""
                <div class="explanation-box">
                    <strong>Explanation:</strong><br>
                    "{rec['explanation']}"
                </div>
                """
            else:
                expl_html = """
                <div class="no-expl-box">
                </div>
                """

            rec_key = f"p{p_idx+1}_r{r_idx+1}" 
            
            html_content += f"""
                <div class="recipe-card">
                    <div class="recipe-header">
                        <div class="d-flex justify-content-between align-items-center">
                            <h5 class="m-0">#{r_idx + 1} {rec['title']}</h5>
                            <span class="text-muted small">ID: {rec['recipe_id']}</span>
                        </div>
                        <div class="mt-2">
                            <span class="nutri-badge">🔥 {nutri.get('calories', 'N/A')} kcal</span>
                            <span class="nutri-badge">🥩 {nutri.get('protein', 'N/A')} Prot</span>
                            <span class="nutri-badge">🍞 {nutri.get('carbs', 'N/A')} Carb</span>
                            <span class="nutri-badge">🥑 {nutri.get('fat', 'N/A')} Fat</span>
                        </div>
                    </div>
                    <div class="recipe-body">
                        <p class="ing-list"><strong>Ingredients:</strong> {ingredients_list}</p>
                        {expl_html}
                        
                        <div class="eval-row">
                            <div class="row g-3">
                                <div class="col-md-4">
                                    <label class="form-label">Relevance (1-5)</label>
                                    <select class="form-select form-select-sm eval-input" data-key="{rec_key}_rel">
                                        <option value="">-</option><option value="1">1 (Poor)</option><option value="2">2</option><option value="3">3</option><option value="4">4</option><option value="5">5 (Perfect)</option>
                                    </select>
                                </div>
                                <div class="col-md-4">
                                    <label class="form-label">Transparency (1-5)</label>
                                    <select class="form-select form-select-sm eval-input" data-key="{rec_key}_trans">
                                        <option value="">-</option><option value="1">1 (Poor)</option><option value="2">2</option><option value="3">3</option><option value="4">4</option><option value="5">5 (Clear)</option>
                                    </select>
                                </div>
                                <div class="col-md-4">
                                    <label class="form-label">Persuasiveness (1-5)</label>
                                    <select class="form-select form-select-sm eval-input" data-key="{rec_key}_pers">
                                        <option value="">-</option><option value="1">1 (Poor)</option><option value="2">2</option><option value="3">3</option><option value="4">4</option><option value="5">5 (Strong)</option>
                                    </select>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            """
        
        html_content += """
            </div>
        </div>
        """

    # --- Footer Script ---
    html_content += f"""
        <div class="sticky-footer">
            <div>
                <button class="btn btn-outline-danger me-2" onclick="resetAll()">🗑️ Reset</button>
                <button class="btn btn-outline-primary" onclick="document.getElementById('fileInput').click()">📂 Load JSON</button>
                <input type="file" id="fileInput" accept=".json" onchange="loadFromFile(this)">
            </div>
            
            <span class="text-muted small" id="statusMsg">Ready. Auto-save enabled.</span>
            
            <button class="btn btn-success" onclick="exportData()">💾 Save & Export JSON</button>
        </div>

        <script>
            const PRELOADED_DATA = {preloaded_json};

            document.addEventListener("DOMContentLoaded", function() {{
                const inputs = document.querySelectorAll(".eval-input");
                let loadedCount = 0;

                // Function to update visual state (Green Box)
                function updateState(input) {{
                    if (input.value && input.value !== "") {{
                        input.classList.add("filled");
                    }} else {{
                        input.classList.remove("filled");
                    }}
                }}

                inputs.forEach(input => {{
                    const key = input.dataset.key;
                    
                    // Load Data
                    const savedLocal = localStorage.getItem("xfood_" + key);
                    const savedPython = PRELOADED_DATA[key];

                    if (savedLocal) {{
                        input.value = savedLocal;
                        loadedCount++;
                    }} else if (savedPython) {{
                        input.value = savedPython;
                        localStorage.setItem("xfood_" + key, savedPython);
                        loadedCount++;
                    }}
                    
                    // Initial State
                    updateState(input);

                    // Change Listener
                    input.addEventListener("change", function() {{
                        localStorage.setItem("xfood_" + this.dataset.key, this.value);
                        updateState(this);
                        document.getElementById('statusMsg').innerText = "Saved change.";
                    }});
                }});
                
                if(loadedCount > 0) document.getElementById('statusMsg').innerText = "Restored " + loadedCount + " answers.";
            }});

            function resetAll() {{
                if (confirm("Clear all answers? This cannot be undone.")) {{
                    document.querySelectorAll(".eval-input").forEach(input => {{
                        input.value = "";
                        input.classList.remove("filled");
                        localStorage.removeItem("xfood_" + input.dataset.key);
                    }});
                    document.getElementById('statusMsg').innerText = "All cleared.";
                }}
            }}

            function exportData() {{
                const data = {{}};
                const inputs = document.querySelectorAll(".eval-input");
                let missingCount = 0;
                
                // 1. Validate Name
                const nameField = document.querySelector('input[data-key="evaluator_name"]');
                if (!nameField.value) {{
                    alert("⚠️ Please enter your name at the top of the page before exporting.");
                    nameField.focus();
                    window.scrollTo(0, 0);
                    return;
                }}
                data[nameField.dataset.key] = nameField.value;

                // 2. Collect Scores & Count Missing
                inputs.forEach(input => {{
                    if (input.dataset.key === "evaluator_name") return; // Skip name
                    
                    if (input.value) {{
                        data[input.dataset.key] = input.value;
                    }} else {{
                        missingCount++;
                    }}
                }});

                // 3. Validation Message
                if (missingCount > 0) {{
                    const confirmMsg = "⚠️ Warning: You have " + missingCount + " unscored items.\\n\\nDo you want to export incomplete results anyway?";
                    if (!confirm(confirmMsg)) {{
                        return; // Cancel export
                    }}
                }}

                // 4. Download
                const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(data, null, 2));
                const anchor = document.createElement('a');
                anchor.href = dataStr;
                anchor.download = "evaluation_" + nameField.value.replace(/[^a-z0-9]/gi, '_').toLowerCase() + ".json";
                anchor.click();
            }}

            function loadFromFile(input) {{
                const file = input.files[0];
                if (!file) return;
                const reader = new FileReader();
                reader.onload = function(e) {{
                    try {{
                        const data = JSON.parse(e.target.result);
                        document.querySelectorAll(".eval-input").forEach(input => {{
                            if (data[input.dataset.key]) {{
                                input.value = data[input.dataset.key];
                                input.classList.add("filled");
                                localStorage.setItem("xfood_" + input.dataset.key, input.value);
                            }}
                        }});
                        alert("Scores loaded successfully!");
                    }} catch (err) {{ alert("Invalid JSON file"); }}
                }};
                reader.readAsText(file);
                input.value = ''; 
            }}
        </script>
    </div>
    </body>
    </html>
    """

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"✅ Human Evaluation Tool generated: {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_html_report()