import numpy as np
import pytest

from boundevo.coefficients import (
    adaptive_boundary_coefficients,
    edbf_coefficients,
    edbf_probabilities,
    generate_coefficients,
    is_valid_coefficients,
    random_exhaustive_coefficients,
)


@pytest.mark.parametrize("m", [1, 2, 3, 5, 15, 50, 200])
def test_abc_is_always_valid(m: int) -> None:
    rng = np.random.default_rng(7)
    for _ in range(500):
        result = adaptive_boundary_coefficients(m, rng)
        assert result.attempts == 1
        assert result.coefficients.shape == (m,)
        assert is_valid_coefficients(result.coefficients)


def test_abc_is_reproducible() -> None:
    a = adaptive_boundary_coefficients(15, np.random.default_rng(42)).coefficients
    b = adaptive_boundary_coefficients(15, np.random.default_rng(42)).coefficients
    np.testing.assert_allclose(a, b)


@pytest.mark.parametrize("generator", [random_exhaustive_coefficients, edbf_coefficients])
def test_rejection_generators_return_valid_vectors(generator) -> None:
    result = generator(8, np.random.default_rng(10))
    assert result.attempts >= 1
    assert is_valid_coefficients(result.coefficients)


@pytest.mark.parametrize("m", [2, 5, 10, 15, 20, 100])
def test_edbf_probabilities_are_valid(m: int) -> None:
    probs = edbf_probabilities(m)
    assert all(0.0 <= p <= 1.0 for p in probs)
    assert sum(probs) == pytest.approx(1.0)


def test_dispatch_rejects_unknown_method() -> None:
    with pytest.raises(ValueError):
        generate_coefficients(4, method="missing")  # type: ignore[arg-type]
