"""Compare coefficient-generation effort for RE, EDBF, and ABC.

This script reports attempts per accepted coefficient vector.  ABC always needs
one attempt; the rejection methods become less efficient as M grows.
"""

from __future__ import annotations

import argparse
import time

import numpy as np

from boundevo.coefficients import generate_coefficients


def benchmark(method: str, m: int, repeats: int, seed: int) -> tuple[float, float:
    rng = np.random.default_rng(seed)
    attempts = 0
    start = time.perf_counter()
    for _ in range(repeats):
        result = generate_coefficients(m, method=method, rng=rng)
        attempts += result.attempts
    elapsed = time.perf_counter() - start
    return attempts / repeats, elapsed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-m", type=int, default=2)
    parser.add_argument("--max-m", type=int, default=20)
    parser.add_argument("--repeats", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    print("M,method,mean_attempts,seconds")
    for m in range(args.min_m, args.max_m + 1):
        for method in ("re", "edbf", "abc"):
            mean_attempts, elapsed = benchmark(method, m, args.repeats, args.seed + m)
            print(f"{m},{method},{mean_attempts:.6f},{elapsed:.6f}")


if __name__ == "__main__":
    main()
