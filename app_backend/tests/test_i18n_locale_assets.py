from pathlib import Path

import pytest


def test_japanese_locale_assets_are_available_under_core(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAIN_APP_LOCALE", "ja_JP")

    from core.i18n import LocaleSettings

    settings = LocaleSettings()
    locale_dir = Path(settings.get_locale_dir())
    locale_messages_dir = locale_dir / "ja_JP" / "LC_MESSAGES"

    assert locale_messages_dir.is_dir()
    assert (locale_messages_dir / "base.po").is_file()

    settings.setup_locale()

    assert (locale_messages_dir / "base.mo").is_file()
