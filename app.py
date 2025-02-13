# app.py
import json
import math
from collections import defaultdict
from flask import Flask, render_template, request, jsonify
import pandas as pd
import plotly.express as px

app = Flask(__name__)

# Load questions and character data
with open("quiz\got_quiz.json", "r") as f:
    questions_data = json.load(f)

with open("character_profile\got_char_profiles_norm.json", "r") as f:
    character_data = json.load(f)

# Initialize question mapping
question_mapping = {}
counter = 1
for trait in questions_data:
    for question in questions_data[trait]:
        question_mapping[f'q{counter}'] = trait
        counter += 1

def calculate_similarity(user_scores, character_scores):
    """Calculate cosine similarity between user and character vectors"""
    dot_product = sum(user_scores[t] * character_scores[t] for t in user_scores)
    user_magnitude = math.sqrt(sum(score**2 for score in user_scores.values()))
    char_magnitude = math.sqrt(sum(score**2 for score in character_scores.values()))
    
    if user_magnitude * char_magnitude == 0:
        return 0
    return dot_product / (user_magnitude * char_magnitude)

def find_character_match(user_scores):
    """Find best character match with similarity score"""
    best_match = None
    max_similarity = -1
    
    for char_name, char_scores in character_data.items():
        similarity = calculate_similarity(user_scores, char_scores)
        if similarity > max_similarity:
            max_similarity = similarity
            best_match = char_name.title()  # Proper capitalization
    return best_match, max_similarity

def plot_interactive_radar_chart(scores, user_scores=None):
    """Plot an interactive radar chart comparing characters and user scores."""
    # Create a copy of scores to avoid modifying the original
    plot_data = scores.copy()
    
    # Add user data if provided
    if user_scores:
        plot_data["You"] = user_scores
    
    traits = list(next(iter(plot_data.values())).keys())
    
    # Transform data for radar chart
    data = []
    for char, values in plot_data.items():
        row = {"Character": char}
        row.update(values)
        data.append(row)
    
    df = pd.DataFrame(data)
    fig = px.line_polar(
        df.melt(id_vars=["Character"], var_name="Trait", value_name="Score"),
        r="Score",
        theta="Trait",
        color="Character",
        line_close=True,
        hover_data=["Score"],
    )
    
    # Update hover template
    fig.update_traces(
        hovertemplate="<b>Character:</b> %{customdata[0]}<br><b>Trait:</b> %{theta}<br><b>Score:</b> %{r:.2f}"
    )
    
    # Highlight user data if present
    if user_scores:
        fig.update_traces(
            line=dict(width=3),
            selector=dict(name="You")
        )
    
    fig.update_layout(
        title="Your Personality Match Comparison",
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
    )
    
    return fig

# Example usage:
#plot_interactive_radar_chart(character_profiles, user_scores)


@app.route('/')
def index():
    return render_template("index.html", questions_data=questions_data)

@app.route('/submit', methods=['POST'])
def submit():
    try:
        data = request.get_json()
        answers = data.get('answers', {})

        # Calculate raw trait scores
        trait_scores = defaultdict(float)
        for q_id, score in answers.items():
            trait = question_mapping.get(q_id)
            if trait:
                trait_scores[trait] += float(score)
        
        # Normalize scores
        questions_per_trait = {t: len(q) for t, q in questions_data.items()}
        normalized_scores = {
            trait: score / questions_per_trait[trait]
            for trait, score in trait_scores.items()
        }
        
        # Find best match
        match, similarity = find_character_match(normalized_scores)
        
        # Generate plot
        fig = plot_interactive_radar_chart(character_data, normalized_scores)
        plot_json = fig.to_json()

        return jsonify({
            'match': match,
            'similarity': similarity,
            'scores': normalized_scores,
            'plot': plot_json
        })
    except Exception as e:
        app.logger.error(f"Error processing submission: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True)

# render deployment
#if __name__ == '__main__':
#    app.run(host="0.0.0.0", port=10000)  # Use Render's default port

