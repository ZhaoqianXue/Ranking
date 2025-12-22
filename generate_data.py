import pandas as pd
import random
import numpy as np

# Configuration
target_rows = 2400
models = ['ChatGPT', 'Gemini', 'Claude', 'Your Model', 'Llama', 'Qwen']
# Defined hierarchy scores (higher is better)
# Using Elo-like logic: P(A wins B) = 1 / (1 + 10^((Rb - Ra)/400))
# Adjusted gaps to create realistic overlaps (CIs that are narrow but not single-point)
elo_scores = {
    'ChatGPT': 1250,
    'Gemini': 1180,   # Gap 70 -> ~59% win rate vs 1250
    'Claude': 1120,   # Gap 60
    'Your Model': 1070, # Gap 50
    'Llama': 1020,    # Gap 50
    'Qwen': 950       # Gap 70 (clearer loser)
}

# Tasks
tasks = ['code', 'math']

rows = []

for _ in range(target_rows):
    # Select 2 distinct models
    m1, m2 = random.sample(models, 2)
    
    # Calculate win prob for m1
    # Logistic function based on score diff
    score_diff = elo_scores[m1] - elo_scores[m2]
    # Standard Elo divisor is 400.
    # Using 350 to allow some noise but keep rankings fairly stable
    prob_m1_win = 1 / (1 + 10 ** (-score_diff / 350))
    
    # Determine winner
    if random.random() < prob_m1_win:
        winner, loser = m1, m2
    else:
        winner, loser = m2, m1
        
    # Create row dict
    row = {
        'Task': random.choice(tasks),
        'Your Model': '',
        'ChatGPT': '',
        'Claude': '',
        'Gemini': '',
        'Llama': '',
        'Qwen': ''
    }
    
    # Integer assignments
    row[winner] = 1
    row[loser] = 0
    
    rows.append(row)

# Create DataFrame
df = pd.DataFrame(rows)

# Ensure column order matches original exactly
cols = ['Task', 'Your Model', 'ChatGPT', 'Claude', 'Gemini', 'Llama', 'Qwen']
df = df[cols]

# Save
df.to_csv('demo_r/example_arena_style.csv', index=False)
print(f"Generated {len(df)} rows to demo_r/example_arena_style.csv")
