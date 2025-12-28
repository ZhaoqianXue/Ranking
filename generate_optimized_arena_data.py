import pandas as pd
import numpy as np
import random

# Set random seed for reproducibility
np.random.seed(42)
random.seed(42)

# Models to compare
models = ['ChatGPT', 'Claude', 'Gemini', 'Llama', 'Qwen', 'Your Model']

# Task types (indicators)
tasks = ['code', 'math', 'writing']

# Define true skill levels for each model on each task type
# INCREASED differentiation to make rankings more distinct
model_skills = {
    # Task:    code,  math,  writing
    'ChatGPT':   [0.68, 0.45, 0.80],   # DOMINANT at writing, weak at math
    'Claude':    [0.62, 0.75, 0.70],   # DOMINANT at math, good all-around
    'Gemini':    [0.58, 0.78, 0.50],   # DOMINANT at math, very weak at writing
    'Llama':     [0.52, 0.60, 0.58],   # Consistent mid-tier
    'Qwen':      [0.78, 0.55, 0.48],   # DOMINANT at code, weak at writing
    'Your Model':[0.48, 0.52, 0.65],   # Weakest overall, decent at writing
}

# Create a mapping from task name to index
task_to_idx = {'code': 0, 'math': 1, 'writing': 2}

def generate_comparison(task, model_a, model_b):
    """
    Generate a comparison result based on true skills.
    Returns 1 if model_a wins, 0 if model_b wins.
    """
    task_idx = task_to_idx[task]
    skill_a = model_skills[model_a][task_idx]
    skill_b = model_skills[model_b][task_idx]
    
    # Use Bradley-Terry model: P(A beats B) = skill_a / (skill_a + skill_b)
    prob_a_wins = skill_a / (skill_a + skill_b)
    
    # Reduce noise to make skill differences more apparent (±0.03 instead of ±0.05)
    prob_a_wins = np.clip(prob_a_wins + np.random.normal(0, 0.03), 0.15, 0.85)
    
    return 1 if random.random() < prob_a_wins else 0

# INCREASED comparisons per pair to narrow confidence intervals
# 100 comparisons per pair per task should give CI width < 0.2
comparisons_per_pair_per_task = 100
total_model_pairs = len(models) * (len(models) - 1) // 2  # 15 pairs
total_rows = comparisons_per_pair_per_task * total_model_pairs * len(tasks)

print(f"Generating {total_rows} comparisons...")
print(f"  - {len(tasks)} task types")
print(f"  - {total_model_pairs} model pairs")
print(f"  - {comparisons_per_pair_per_task} comparisons per pair per task")
print()

rows = []

for task in tasks:
    for i, model_a in enumerate(models):
        for j, model_b in enumerate(models):
            if i < j:  # Only compare each pair once
                # Generate multiple comparisons for this pair on this task
                for _ in range(comparisons_per_pair_per_task):
                    row = {task_col: '' for task_col in ['Task'] + models}
                    row['Task'] = task
                    
                    result = generate_comparison(task, model_a, model_b)
                    row[model_a] = result
                    row[model_b] = 1 - result
                    
                    rows.append(row)

# Shuffle to randomize order
random.shuffle(rows)

# Create DataFrame
df = pd.DataFrame(rows)

# Verify row count
print(f"Total rows generated: {len(df)}")
print(f"Rows per task type:")
for task in tasks:
    task_count = len(df[df['Task'] == task])
    print(f"  - {task}: {task_count} rows")

# Save to CSV
output_path = 'demo_r/example_arena_style.csv'
df.to_csv(output_path, index=False)
print(f"\n✅ Saved optimized dataset to {output_path}")

# Show expected rankings per task type
print("\n📊 Expected Rankings by Task Type:")
print("=" * 60)
for task in tasks:
    print(f"\n{task.upper()} Task:")
    task_idx = task_to_idx[task]
    rankings = sorted(models, key=lambda m: model_skills[m][task_idx], reverse=True)
    for rank, model in enumerate(rankings, 1):
        skill = model_skills[model][task_idx]
        print(f"  {rank}. {model:12s} (skill: {skill:.2f})")

print("\n" + "=" * 60)
print("\n✅ Dataset optimized for:")
print("  ✓ Total rows: ", len(df), "(< 5000)")
print("  ✓ Narrow confidence intervals (100 comparisons per pair per task)")
print("  ✓ Distinct θ-hat scores (models have clearly different skill levels)")
print("  ✓ Different rankings per task combination")
print("\nExpected results:")
print("  • code only → Qwen dominates")
print("  • math only → Gemini/Claude dominate")
print("  • writing only → ChatGPT dominates")
print("  • Different combinations → Different rankings")
