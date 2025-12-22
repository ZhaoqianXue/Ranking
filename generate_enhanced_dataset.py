#!/usr/bin/env python3
"""
Generate an enhanced arena-style dataset with three task types: code, math, writing
Design different models to excel at different tasks to produce diverse rankings
"""

import csv
import random
import itertools

# Model names
MODELS = ['Your Model', 'ChatGPT', 'Claude', 'Gemini', 'Llama', 'Qwen']

# Task-specific model strengths (win probability when this model is selected)
# Higher values = more likely to win in this task type
TASK_STRENGTHS = {
    'code': {
        'ChatGPT': 0.75,    # Strongest in code
        'Claude': 0.70,     # 2nd strongest
        'Gemini': 0.55,     
        'Qwen': 0.50,
        'Your Model': 0.45,
        'Llama': 0.40       # Weakest in code
    },
    'math': {
        'Gemini': 0.75,     # Strongest in math
        'Qwen': 0.70,       # 2nd strongest
        'ChatGPT': 0.55,
        'Claude': 0.50,
        'Llama': 0.45,
        'Your Model': 0.40  # Weakest in math
    },
    'writing': {
        'Claude': 0.75,     # Strongest in writing
        'Your Model': 0.70, # 2nd strongest (Your Model shines here!)
        'ChatGPT': 0.60,
        'Gemini': 0.50,
        'Llama': 0.45,
        'Qwen': 0.35        # Weakest in writing
    }
}

def generate_comparison(task, model1, model2, strength_dict):
    """Generate a single pairwise comparison"""
    # Get win probabilities
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

def generate_dataset(samples_per_task=800, seed=42):
    """
    Generate arena-style dataset with balanced comparisons
    
    Args:
        samples_per_task: Number of comparisons per task type
        seed: Random seed for reproducibility
    """
    random.seed(seed)
    
    rows = []
    header = ['Task'] + MODELS
    
    tasks = ['code', 'math', 'writing']
    
    for task in tasks:
        print(f"Generating {samples_per_task} samples for task: {task}")
        
        # Get all possible model pairs
        model_pairs = list(itertools.combinations(MODELS, 2))
        
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
                for model in MODELS:
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
    print("Generating Enhanced Arena-Style Dataset")
    print("="*70)
    print("\nTask-specific model strengths:")
    print("\nCode tasks (ranked by strength):")
    print("  1. ChatGPT (0.75)")
    print("  2. Claude (0.70)")
    print("  3. Gemini (0.55)")
    print("  ...(lower ranks)")
    
    print("\nMath tasks (ranked by strength):")
    print("  1. Gemini (0.75)")
    print("  2. Qwen (0.70)")
    print("  3. ChatGPT (0.55)")
    print("  ...(lower ranks)")
    
    print("\nWriting tasks (ranked by strength):")
    print("  1. Claude (0.75)")
    print("  2. Your Model (0.70) <- Your Model excels here!")
    print("  3. ChatGPT (0.60)")
    print("  ...(lower ranks)")
    
    print("\n" + "="*70)
    print("Expected ranking differences:")
    print("="*70)
    print("Code only: ChatGPT, Claude, Gemini, ...")
    print("Math only: Gemini, Qwen, ChatGPT, ...")
    print("Writing only: Claude, Your Model, ChatGPT, ...")
    print("Code+Math: ChatGPT, Gemini, Claude, ...")
    print("All three: Balanced based on overall performance")
    print("="*70)
    
    # Generate dataset with more samples per task for tighter confidence intervals
    header, rows = generate_dataset(samples_per_task=1000, seed=42)
    
    # Save to file
    output_file = 'demo_r/example_arena_style_enhanced.csv'
    save_dataset(output_file, header, rows)
    
    print(f"\n✅ Enhanced dataset created: {output_file}")
    print(f"   Total samples: {len(rows)}")
    print(f"   Task types: code, math, writing")
    print(f"   Models: {', '.join(MODELS)}")

if __name__ == "__main__":
    main()
