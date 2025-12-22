#!/usr/bin/env python3
"""
Generate optimized arena-style dataset with:
1. Narrower confidence intervals (more samples)
2. Larger theta-hat differences (bigger strength gaps)
3. ChatGPT, Gemini, Claude always in top 3 overall
"""

import csv
import random
import itertools

# Model names - split into two tiers
TOP_TIER = ['ChatGPT', 'Gemini', 'Claude']
LOWER_TIER = ['Your Model', 'Llama', 'Qwen']
ALL_MODELS = TOP_TIER + LOWER_TIER

# Task-specific model strengths - INCREASED GAPS for larger theta-hat differences
# Top tier: 0.75-0.90, Lower tier: 0.25-0.35
TASK_STRENGTHS = {
    'code': {
        # Top tier dominates
        'ChatGPT': 0.90,    # Strongest in code
        'Claude': 0.82,     
        'Gemini': 0.75,     
        # Lower tier much weaker
        'Your Model': 0.35,
        'Qwen': 0.28,
        'Llama': 0.25       # Weakest
    },
    'math': {
        # Top tier dominates (Gemini leads)
        'Gemini': 0.90,     # Strongest in math
        'Claude': 0.80,     
        'ChatGPT': 0.75,
        # Lower tier much weaker
        'Qwen': 0.35,       
        'Your Model': 0.28,
        'Llama': 0.25
    },
    'writing': {
        # Top tier dominates (Claude leads)
        'Claude': 0.90,     # Strongest in writing
        'ChatGPT': 0.82,
        'Gemini': 0.75,
        # Lower tier much weaker (but Your Model slightly better here)
        'Your Model': 0.38,  # Best among lower tier
        'Llama': 0.28,
        'Qwen': 0.25
    }
}

def generate_comparison(task, model1, model2, strength_dict):
    """Generate a single pairwise comparison"""
    p1 = strength_dict[task][model1]
    p2 = strength_dict[task][model2]
    
    # Normalize to get actual win probability for model1
    total = p1 + p2
    win_prob = p1 / total
    
    # Determine winner
    if random.random() < win_prob:
        return {model1: 1, model2: 0}
    else:
        return {model1: 0, model2: 1}

def generate_dataset(samples_per_task=2500, seed=42):
    """
    Generate arena-style dataset with more samples for tighter CIs
    
    Args:
        samples_per_task: Number of comparisons per task (increased to 2500)
        seed: Random seed for reproducibility
    """
    random.seed(seed)
    
    rows = []
    header = ['Task'] + ALL_MODELS
    
    tasks = ['code', 'math', 'writing']
    
    for task in tasks:
        print(f"Generating {samples_per_task} samples for task: {task}")
        
        # Get all possible model pairs
        model_pairs = list(itertools.combinations(ALL_MODELS, 2))
        
        # For each pair, generate multiple comparisons
        comparisons_per_pair = samples_per_task // len(model_pairs)
        extra_comparisons = samples_per_task % len(model_pairs)
        
        for i, (model1, model2) in enumerate(model_pairs):
            # Generate base comparisons
            num_comparisons = comparisons_per_pair
            
            # Add extra comparisons to first few pairs
            if i < extra_comparisons:
                num_comparisons += 1
            
            for _ in range(num_comparisons):
                result = generate_comparison(task, model1, model2, TASK_STRENGTHS)
                
                # Create row
                row = {'Task': task}
                for model in ALL_MODELS:
                    row[model] = result.get(model, '')
                
                rows.append(row)
    
    # Shuffle all rows
    random.shuffle(rows)
    
    return header, rows

def save_dataset(filename, header, rows):
    """Save dataset to CSV file"""
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"\nSaved {len(rows)} rows to {filename}")
    
    # Print statistics
    task_counts = {}
    for row in rows:
        task = row['Task']
        task_counts[task] = task_counts.get(task, 0) + 1
    
    print("\nTask distribution:")
    for task, count in sorted(task_counts.items()):
        print(f"  {task}: {count} samples")

def main():
    print("="*70)
    print("Generating Optimized Arena-Style Dataset")
    print("="*70)
    
    print("\n📊 OPTIMIZATION GOALS:")
    print("  1. ✅ Narrower CI: 2,500 samples per task (vs 1,000)")
    print("  2. ✅ Larger θ-hat gaps: Strength difference 0.65 (0.90 vs 0.25)")
    print("  3. ✅ Top 3: ChatGPT, Gemini, Claude always dominate")
    
    print("\n🎯 Task-specific leaders (all from top tier):")
    print("  Code:    ChatGPT (0.90) > Claude (0.82) > Gemini (0.75)")
    print("  Math:    Gemini (0.90) > Claude (0.80) > ChatGPT (0.75)")
    print("  Writing: Claude (0.90) > ChatGPT (0.82) > Gemini (0.75)")
    
    print("\n📉 Lower tier (always weaker: 0.25-0.38):")
    print("  Your Model, Llama, Qwen")
    
    print("\n" + "="*70)
    
    # Generate dataset with MORE samples for tighter CIs
    header, rows = generate_dataset(samples_per_task=2500, seed=42)
    
    # Save to file
    output_file = 'demo_r/example_arena_style.csv'
    save_dataset(output_file, header, rows)
    
    print(f"\n✅ Optimized dataset created: {output_file}")
    print(f"   Total samples: {len(rows)} (2,500 per task × 3 tasks)")
    print(f"   Expected CI width: ~50% narrower than before")
    print(f"   Expected θ-hat range: ~1.5 (top tier 0.5 to 1.0, lower tier -1.0 to -0.5)")

if __name__ == "__main__":
    main()
