"""Scientific pairing and benchmark-backend dispatch regression tests."""

from boundevo import experiments, sweep
from boundevo.cli import build_parser


def test_benchmark_methods_share_initial_seed(monkeypatch) -> None:
    captured = []
    monkeypatch.setattr(
        experiments,
        "make_cec2017_case",
        lambda fid, dimension, backend: (fid, dimension, backend),
    )

    def fake_run(case, **kwargs):
        captured.append((case, kwargs["method"], kwargs["repeat"], kwargs["seed"]))
        return kwargs["seed"]

    monkeypatch.setattr(experiments, "run_case", fake_run)
    result = experiments.run_cec2017_suite(
        function_ids=[1],
        dimension=10,
        backend="reference",
        methods=("abc", "edbf", "re"),
        repeats=3,
        base_seed=7,
        max_evaluations=100,
    )
    assert len(result) == 9
    for repeat in range(3):
        matched = [row for row in captured if row[2] == repeat]
        assert {row[1] for row in matched} == {"abc", "edbf", "re"}
        assert {row[3] for row in matched} == {10007 + repeat}
        assert all(row[0] == (1, 10, "reference") for row in matched)


def test_parent_sweep_methods_share_initial_seed(monkeypatch) -> None:
    captured = []
    monkeypatch.setattr(
        sweep,
        "make_cec2017_case",
        lambda fid, dimension, backend: (fid, dimension, backend),
    )

    def fake_run(case, **kwargs):
        captured.append((kwargs["parent_count"], kwargs["method"], kwargs["seed"]))
        return kwargs["seed"]

    monkeypatch.setattr(sweep, "run_parent_sweep_case", fake_run)
    result = sweep.run_parent_count_sweep(
        function_ids=[1],
        parent_counts=[10, 11],
        dimension=10,
        backend="reference",
        methods=("abc", "edbf", "re"),
        repeats=1,
        base_seed=7,
        max_evaluations=100,
    )
    assert len(result) == 6
    for count in (10, 11):
        matched = [row for row in captured if row[0] == count]
        assert {row[1] for row in matched} == {"abc", "edbf", "re"}
        assert len({row[2] for row in matched}) == 1


def test_cli_explicit_reference_backend() -> None:
    parser = build_parser()
    for name in ("benchmark", "sweep", "pipeline"):
        args = parser.parse_args([name, "--backend", "reference"])
        assert args.backend == "reference"
