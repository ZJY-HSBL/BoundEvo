"""BoundEvo: adaptive-boundary multi-parent evolutionary optimization."""

from .coefficients import (
    GenerationResult,
    adaptive_boundary_coefficients,
    edbf_coefficients,
    edbf_probabilities,
    generate_coefficients,
    is_valid_coefficients,
    random_exhaustive_coefficients,
)
from .optimizer import BoundEvo, BoundEvoConfig, OptimizationResult, OptimizationState
from .problem import Evaluation, OptimizationProblem, better, evaluation_key

__all__ = [
    "BoundEvo",
    "BoundEvoConfig",
    "Evaluation",
    "GenerationResult",
    "OptimizationProblem",
    "OptimizationResult",
    "OptimizationState",
    "adaptive_boundary_coefficients",
    "better",
    "edbf_coefficients",
    "edbf_probabilities",
    "evaluation_key",
    "generate_coefficients",
    "is_valid_coefficients",
    "random_exhaustive_coefficients",
]

__version__ = "0.5.0.dev0"
