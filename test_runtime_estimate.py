#!/usr/bin/env python3
"""
Test the optimized runtime estimation formula
"""

import asyncio
import math

# Simulate the new estimation logic
def estimate_runtime(n_samples: int, k_methods: int, B: int) -> float:
    """New optimized runtime estimation"""
    if n_samples <= 0 or k_methods <= 0 or B <= 0:
        return 0

    # Benchmark: 163 samples, 6 methods, B=2000 takes ~1 second
    reference_time = 1.0  # seconds
    reference_samples = 163
    reference_methods = 6
    reference_bootstrap = 2000

    # Calculate scaling factors
    sample_ratio = n_samples / reference_samples
    method_ratio = k_methods / reference_methods
    bootstrap_ratio = B / reference_bootstrap

    # Complexity analysis based on R script:
    # 1. Data preprocessing: O(n_samples * k_methods^2)
    # 2. Matrix operations: O(n_samples * k_methods^3)
    # 3. Bootstrap: O(B * n_samples * k_methods^2)

    # Estimate time using power-law scaling
    preprocessing_factor = sample_ratio * (method_ratio ** 2)
    matrix_factor = sample_ratio * (method_ratio ** 3)
    bootstrap_factor = bootstrap_ratio * sample_ratio * (method_ratio ** 2)

    # Weighted combination based on actual bottlenecks
    est_seconds = reference_time * (
        0.1 * preprocessing_factor +     # 10% preprocessing
        0.2 * matrix_factor +           # 20% matrix operations
        0.7 * bootstrap_factor          # 70% bootstrap (bottleneck)
    )

    # Minimum time bounds
    est_seconds = max(0.5, min(est_seconds, 300))  # 0.5s to 5min

    return est_seconds

def format_time(seconds: float) -> str:
    """Format seconds to readable time"""
    if seconds < 60:
        return f"{int(seconds)} seconds"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        seconds_remain = int(seconds % 60)
        return f"{minutes}m {seconds_remain}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"

def test_scenarios():
    """Test various scenarios"""
    scenarios = [
        # Reference benchmark
        (163, 6, 2000, "Benchmark (actual ~1s)"),

        # Scale up samples
        (326, 6, 2000, "2x samples"),
        (815, 6, 2000, "5x samples"),

        # Scale up methods
        (163, 12, 2000, "2x methods"),
        (163, 18, 2000, "3x methods"),

        # Scale up bootstrap
        (163, 6, 4000, "2x bootstrap"),
        (163, 6, 10000, "5x bootstrap"),

        # Real-world scenarios
        (1000, 10, 2000, "Large dataset"),
        (100, 5, 1000, "Small dataset"),
        (500, 8, 5000, "Medium-large dataset"),
    ]

    print("🧮 RUNTIME ESTIMATION TEST")
    print("=" * 60)
    print(f"{'Scenario':<25} {'Samples':<8} {'Methods':<8} {'B':<8} {'Est. Time':<12}")
    print("-" * 80)

    for n_samples, k_methods, B, description in scenarios:
        est_seconds = estimate_runtime(n_samples, k_methods, B)
        time_str = format_time(est_seconds)
        print(f"{description:<25} {n_samples:<8} {k_methods:<8} {B:<8} {time_str:<12}")

    print("\n✅ Benchmark validation:")
    benchmark_time = estimate_runtime(163, 6, 2000)
    print(f"Benchmark (163 samples, 6 methods, B=2000): {benchmark_time:.1f} seconds (expected ~1.0s)")
if __name__ == "__main__":
    test_scenarios()