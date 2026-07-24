from __future__ import annotations

import importlib.util
import logging
import sys
import types
from datetime import date
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).parents[1]
DASHBOARD_DIR = REPO_ROOT / "resources" / "app_usage_dashboard"
APP_SOURCE = DASHBOARD_DIR / "app.py"
VISUALIZATIONS_SOURCE = DASHBOARD_DIR / "visualizations.py"


def _load_visualizations(monkeypatch):
    streamlit = types.ModuleType("streamlit")
    streamlit_logger = types.ModuleType("streamlit.logger")
    streamlit_logger.get_logger = logging.getLogger
    wordcloud = types.ModuleType("wordcloud")
    wordcloud.WordCloud = object
    i18n_setup = types.ModuleType("i18n_setup")
    i18n_setup._ = lambda key, **kwargs: key

    monkeypatch.setitem(sys.modules, "streamlit", streamlit)
    monkeypatch.setitem(sys.modules, "streamlit.logger", streamlit_logger)
    monkeypatch.setitem(sys.modules, "wordcloud", wordcloud)
    monkeypatch.setitem(sys.modules, "i18n_setup", i18n_setup)

    spec = importlib.util.spec_from_file_location(
        "app_usage_dashboard_visualizations",
        VISUALIZATIONS_SOURCE,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_unexpected_finish_trend_counts_true_rows_by_period(monkeypatch) -> None:
    visualizations = _load_visualizations(monkeypatch)
    trace_chat = pd.DataFrame(
        {
            "date": [date(2026, 7, 23), date(2026, 7, 23), date(2026, 7, 24)],
            "stopUnexpected": [True, False, True],
        }
    )

    figure = visualizations.plot_unexpected_finish_trend(
        trace_chat,
        (date(2026, 7, 23), date(2026, 7, 24)),
        "D",
    )

    assert list(figure.data[0].y) == [1, 1]


def test_dashboard_uses_streamlit_width_parameter() -> None:
    app_source = APP_SOURCE.read_text()

    assert "use_container_width=" not in app_source
    assert app_source.count('width="stretch"') == 9
