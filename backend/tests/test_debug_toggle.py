"""调试标签开关的静态测试。

项目无前端 JS 测试框架，这里校验 index.html 源码中开关的实现契约：
默认关闭、不持久化、只影响前端显示、刷新/退出/新建训练后恢复关闭。
"""

from pathlib import Path

STATIC_INDEX = Path(__file__).resolve().parents[1] / "app" / "static" / "index.html"


def _html() -> str:
    return STATIC_INDEX.read_text(encoding="utf-8")


def test_debug_toggle_checkbox_exists_and_default_off():
    html = _html()
    assert 'id="f-debug-tags"' in html
    # 默认未勾选：input 上没有 checked 属性
    assert 'id="f-debug-tags" checked' not in html
    assert 'f-debug-tags" checked' not in html


def test_debug_toggle_not_persisted():
    html = _html()
    # 不写入 localStorage / sessionStorage / 数据库 / 用户配置
    assert "localStorage" not in html
    assert "sessionStorage" not in html


def test_debug_tag_labels_present():
    html = _html()
    for label in (
        "必考问题",
        "AI 动态弹幕",
        "刁难弹幕",
        "无关弹幕",
        "路人弹幕",
        "直播间噪声",
        "冷场提醒",
    ):
        assert label in html


def test_debug_toggle_reset_on_new_training_and_exit():
    html = _html()
    # resetDebugTags 恢复关闭，且 startPractice / backToCreate 都调用它
    assert "function resetDebugTags" in html
    assert "cb.checked = false" in html
    assert html.count("resetDebugTags()") >= 2  # startPractice 与 backToCreate


def test_debug_toggle_only_affects_frontend_rendering():
    html = _html()
    # 开关只改变渲染（DEBUG_TAG_LABELS 是纯前端映射），不携带任何后端参数
    assert "DEBUG_TAG_LABELS" in html
    assert "toggleDebugTags()" in html
    # 标签只在 debugTags 为真时拼接（renderBullets 里按 debugTags 分支）
    assert "debugTags ? (DEBUG_TAG_LABELS" in html
