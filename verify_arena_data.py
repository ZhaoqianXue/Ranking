"""
Verification script to test if the optimized dataset produces different rankings
for different task combinations.
"""
import pandas as pd
import numpy as np

# Load the dataset
df = pd.read_csv('demo_r/example_arena_style.csv')

print("=" * 70)
print("📊 Dataset Verification Report")
print("=" * 70)

# Basic statistics
print(f"\n✓ Total rows: {len(df)}")
print(f"✓ Total columns: {len(df.columns)}")
print(f"✓ Task column: {df.columns[0]}")
print(f"✓ Model columns: {list(df.columns[1:])}")

# Task distribution
print(f"\n📈 Task Distribution:")
task_counts = df['Task'].value_counts().sort_index()
for task, count in task_counts.items():
    print(f"  - {task:10s}: {count:4d} rows ({count/len(df)*100:.1f}%)")

# Check for balance
models = list(df.columns[1:])
print(f"\n⚖️  Data Balance Check:")
for task in df['Task'].unique():
    task_df = df[df['Task'] == task]
    total_comparisons = task_df[models].notna().sum().sum()
    print(f"  - {task:10s}: {total_comparisons:4d} total comparisons")

# Calculate win rates for each model on each task
print(f"\n🎯 Win Rates by Model and Task:")
print("   " + " " * 12 + "Code    Math    Writing")
print("   " + "-" * 45)
for model in models:
    win_rates = []
    for task in ['code', 'math', 'writing']:
        task_df = df[df['Task'] == task]
        total_games = task_df[model].notna().sum()
        wins = task_df[model].sum()
        win_rate = (wins / total_games * 100) if total_games > 0 else 0
        win_rates.append(win_rate)
    
    print(f"   {model:12s}: {win_rates[0]:5.1f}%  {win_rates[1]:5.1f}%  {win_rates[2]:5.1f}%")

# Verify differentiation
print(f"\n✅ Differentiation Verification:")
print("   Checking if different tasks lead to different relative strengths...")

# For code task
code_df = df[df['Task'] == 'code']
code_wins = {model: code_df[model].sum() / code_df[model].notna().sum() 
             for model in models if code_df[model].notna().sum() > 0}
code_ranking = sorted(code_wins.items(), key=lambda x: x[1], reverse=True)

# For math task
math_df = df[df['Task'] == 'math']
math_wins = {model: math_df[model].sum() / math_df[model].notna().sum() 
             for model in models if math_df[model].notna().sum() > 0}
math_ranking = sorted(math_wins.items(), key=lambda x: x[1], reverse=True)

# For writing task
writing_df = df[df['Task'] == 'writing']
writing_wins = {model: writing_df[model].sum() / writing_df[model].notna().sum() 
                for model in models if writing_df[model].notna().sum() > 0}
writing_ranking = sorted(writing_wins.items(), key=lambda x: x[1], reverse=True)

print("\n   Top 3 by task (based on win rate):")
print(f"   Code:    {code_ranking[0][0]:12s} > {code_ranking[1][0]:12s} > {code_ranking[2][0]:12s}")
print(f"   Math:    {math_ranking[0][0]:12s} > {math_ranking[1][0]:12s} > {math_ranking[2][0]:12s}")
print(f"   Writing: {writing_ranking[0][0]:12s} > {writing_ranking[1][0]:12s} > {writing_ranking[2][0]:12s}")

# Check if top model is different for each task
top_models = set([code_ranking[0][0], math_ranking[0][0], writing_ranking[0][0]])
if len(top_models) == 3:
    print("\n   ✅ SUCCESS: Each task has a different top-performing model!")
else:
    print("\n   ⚠️  WARNING: Some tasks share the same top model")

# Estimate confidence interval width (rough approximation)
print(f"\n📏 Confidence Interval Estimation:")
comparisons_per_pair = 40
expected_ci_width = 1.96 * np.sqrt(0.25 / comparisons_per_pair)  # rough estimate
print(f"   With ~{comparisons_per_pair} comparisons per pair per task:")
print(f"   Expected CI half-width: ±{expected_ci_width:.3f}")
print(f"   Expected CI width: {2*expected_ci_width:.3f}")
print(f"   (Narrower is better; < 0.3 is good)")

if 2 * expected_ci_width < 0.3:
    print("   ✅ CI should be reasonably narrow")
else:
    print("   ⚠️  CI might be wider than desired")

print("\n" + "=" * 70)
print("✅ Verification Complete!")
print("=" * 70)
print("\nRecommended test cases:")
print("  1. Select only 'code' → Should favor Qwen/ChatGPT")
print("  2. Select only 'math' → Should favor Gemini/Claude")
print("  3. Select only 'writing' → Should favor ChatGPT/Claude")
print("  4. Select 'code' + 'math' → Should give different ranking")
print("  5. Select all three → Should give balanced ranking")
