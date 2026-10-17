"""Independent C-derived CEC2017 adapter smoke tests."""

import pytest

from boundevo.cec2017 import (
    REFERENCE_COMMIT,
    REFERENCE_REPO,
    make_cec2017_case,
)


def test_reference_backend_dimension_gate() -> None:
    with pytest.raises(ValueError, match="dimensions 10, 30, 50, 100"):
        make_cec2017_case(1, 7, backend="reference")


def test_reference_backend_invalid_choice() -> None:
    with pytest.raises(ValueError, match="backend must"):
        make_cec2017_case(1, 10, backend="not-a-backend")


def test_reference_backend_explicit_source_pin() -> None:
    assert REFERENCE_REPO == "https://github.com/tilleyd/cec2017-py"
    assert len(REFERENCE_COMMIT) == 40
    assert all(character in "0123456789abcdef" for character in REFERENCE_COMMIT)


def test_reference_backend_numerical_smoke() -> None:
    pytest.importorskip("cec2017.functions")
    import numpy as np

    for fid in (1, 3, 10, 30):
        case = make_cec2017_case(fid, 30, backend="reference")
        assert case.problem.dimension == 30
        assert case.optimum == fid * 100.0
        value = case.problem.evaluate(np.zeros(30)).objective
        assert np.isfinite(value)
        assert value >= case.optimum - 1e-7
