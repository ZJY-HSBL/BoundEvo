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


@pytest.mark.parametrize("m", [1, 2, 5, 15, 30])
def test_abc_shuffle_is_valid_and_reproduces_exact_coefficient_multiset(m: int) -> None:
    for seed in range(20):
        original_rng = np.random.default_rng(seed)
        shuffle_rng = np.random.default_rng(seed)
        expected = generate_coefficients(m, method="abc", rng=original_rng)
        observed = generate_coefficients(m, method="abc_shuffle", rng=shuffle_rng)
        assert expected.attempts == observed.attempts == 1
        assert is_valid_coefficients(observed.coefficients)
        np.testing.assert_array_equal(
            np.sort(observed.coefficients), np.sort(expected.coefficients)
        )
        replay = generate_coefficients(
            m, method="abc_shuffle", rng=np.random.default_rng(seed)
        )
        np.testing.assert_array_equal(observed.coefficients, replay.coefficients)


def test_abc_shuffle_changes_coefficient_position_without_changing_values() -> None:
    plain = generate_coefficients(15, method="abc", rng=np.random.default_rng(17))
    shuffled = generate_coefficients(
        15, method="abc_shuffle", rng=np.random.default_rng(17)
    )
    assert not np.array_equal(plain.coefficients, shuffled.coefficients)
    np.testing.assert_array_equal(np.sort(plain.coefficients), np.sort(shuffled.coefficients))


@pytest.mark.parametrize("m", [1, 2, 5, 15, 30])
def test_abc_reverse_preserves_coefficients_and_rng_state(m: int) -> None:
    # The deterministic positional reversal draws exactly the same coefficient
    # values as ABC and MUST NOT consume additional random numbers.
    for seed in range(16):
        left_rng, right_rng = np.random.default_rng(seed), np.random.default_rng(seed)
        abc = generate_coefficients(m, method="abc", rng=left_rng)
        reverse = generate_coefficients(m, method="abc_reverse", rng=right_rng)
        assert abc.attempts == reverse.attempts == 1
        assert is_valid_coefficients(reverse.coefficients)
        np.testing.assert_array_equal(abc.coefficients[::-1], reverse.coefficients)
        assert left_rng.random() == right_rng.random()


def test_abc_reverse_is_actual_position_change_for_m15() -> None:
    abc = generate_coefficients(15, method="abc", rng=np.random.default_rng(20261232))
    reverse = generate_coefficients(
        15, method="abc_reverse", rng=np.random.default_rng(20261232)
    )
    assert not np.array_equal(abc.coefficients, reverse.coefficients)
    np.testing.assert_array_equal(np.sort(abc.coefficients), np.sort(reverse.coefficients))
