from __future__ import annotations

from pathlib import Path

CHANGELOG = Path(__file__).parents[1] / "CHANGELOG.md"


def test_changelog_includes_upstream_v11_5_3_release_notes() -> None:
    changelog = CHANGELOG.read_text()

    assert "## [11.5.3] - 2026-02-26" in changelog
    assert "- Privacy notice when uploading datasets" in changelog
    assert "- Ability to use builder's token for shared applications" in changelog
    assert "- Replaced `tiktoken` token usage predictions with a local algorithm" in changelog
    assert "- Fixed bug with missing builder token" in changelog


def test_changelog_keeps_v11_5_1_and_v11_5_0_upstream_notes() -> None:
    changelog = CHANGELOG.read_text()

    assert "## [11.5.1] - 2026-02-10" in changelog
    assert "- Switched to af-component-llm and replaced all client calls with litellm" in changelog
    assert "- Added flexible LLM options" in changelog
    assert (
        "- Updated LLM configuration system to be more flexible and easier to use "
        "with newer LLMs"
    ) in changelog
