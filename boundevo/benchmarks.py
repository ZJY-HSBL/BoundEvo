"""Small deterministic benchmark set for examples and tests."""

from __future__ import annotations

import numpy as np

from .problem import OptimizationProblem

Array = np.ndarray


def sphere(x: Array) -> float:
    return float(np.dot(x, x))


def rosenbrock(x: Array) -> float:
    return float(np.sum(100.0 * (x[1:] - x[:-1] ** 2) ** 2 + (1.0 - x[:-1]) ** 2))


def rastrigin(x: Array) -> float:
    return float(10.0 * x.size + np.sum(x * x - 10.0 * np.cos(2.0 * np.pi * x)))


def ackley(x: Array) -> float:
    n = x.size
    term1 = -20.0 * np.exp(-0.2 * np.sqrt(np.sum(x * x) / n))
    term2 = -np.exp(np.sum(np.cos(2.0 * np.pi * x)) / n)
    return float(term1 + term2 + 20.0 + np.e)


def make_box_problem(name: str, dimension: int) -> OptimizationProblem:
    if dimension < 1:
        raise ValueError("dimension must be at least 1")
    key = name.lower()
    if key == "sphere":
        return OptimizationProblem(sphere, np.full(dimension, -100.0), np.full(dimension, 100.0))
    if key == "rosenbrock":
        return OptimizationProblem(rosenbrock, np.full(dimension, -30.0), np.full(dimension, 30.0))
    if key == "rastrigin":
        return OptimizationProblem(rastrigin, np.full(dimension, -5.12), np.full(dimension, 5.12))
    if key == "ackley":
        return OptimizationProblem(ackley, np.full(dimension, -32.768), np.full(dimension, 32.768))
    raise ValueError(f"unknown benchmark: {name!r}")
