"""正式 React 训练页调试标签的静态契约。"""

from pathlib import Path

LIVE_PAGE = (
    Path(__file__).resolve().parents[2]
    / "frontend"
    / "src"
    / "pages"
    / "LivePracticeRealPage.tsx"
)


def _source() -> str:
    return LIVE_PAGE.read_text(encoding="utf-8")


def test_debug_toggle_exists_and_defaults_off():
    source = _source()
    assert "显示调试标签" in source
    assert "useState(false)" in source


def test_debug_toggle_not_persisted():
    source = _source()
    assert "localStorage" not in source
    assert "sessionStorage" not in source


def test_debug_tag_labels_present():
    source = _source()
    for label in (
        "必考问题",
        "AI 动态弹幕",
        "刁难弹幕",
        "无关弹幕",
        "路人弹幕",
        "直播间噪声",
        "互动回应",
    ):
        assert label in source


def test_debug_toggle_only_changes_rendering():
    source = _source()
    assert "DEBUG_TAG_LABELS" in source
    assert "debugTags ? <StatusTag" in source
