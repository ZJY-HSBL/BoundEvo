import pytest

from boundevo.pipeline import PipelineConfig


def test_pipeline_config_accepts_source_aligned_defaults() -> None:
    config = PipelineConfig()
    config.validate()
    assert config.parent_counts == tuple(range(10, 17))
    assert config.history_interval == 100
    assert config.statistical_analysis is True


def test_pipeline_allows_single_method_without_statistics() -> None:
    config = PipelineConfig(methods=("abc",), statistical_analysis=False)
    config.validate()


def test_pipeline_requires_three_methods_for_statistics() -> None:
    config = PipelineConfig(methods=("abc",), statistical_analysis=True)
    with pytest.raises(ValueError):
        config.validate()
