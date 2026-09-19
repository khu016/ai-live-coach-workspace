"""弹幕脚本生成（场景卡驱动）。

第一版仍按时间轴触发弹幕，不根据主播实时语音动态变化（依赖流式 ASR，后置实现）。
弹幕文本来自内容库场景卡的 ``reference_utterance``（第一版训练弹幕），
并保留场景元数据供反馈流程回溯。

未审核内容统一以"训练场景"描述，绝不标注为"真实直播原句"。
"""

from . import content_library

# 弹幕下发节奏（秒）
FIRST_AT_SEC = 8
AT_SEC_STEP = 20
# 一次练习最多选取的场景数
MAX_SCENARIOS = 8


def build_script(live_type, goal, topic=None, seed=None):
    """根据直播类型与训练目标挑选场景卡，生成按时间触发的弹幕脚本。"""
    lib = content_library.get_library()
    live_type_en = content_library.LIVE_TYPE_TO_EN.get(live_type)
    if live_type_en is None:
        raise ValueError(f"不支持的直播类型：{live_type!r}")

    must_ids = set(
        content_library.MUST_COVER_SCENARIOS.get(live_type_en, [])
    )
    scenarios = lib.select_scenarios(
        live_type_en,
        goal=goal,
        limit=MAX_SCENARIOS,
        seed=seed,
        include_must=True,
    )

    items = []
    for i, sc in enumerate(scenarios):
        items.append(
            {
                "at_sec": FIRST_AT_SEC + i * AT_SEC_STEP,
                "kind": "fixed_question" if sc["scenario_id"] in must_ids else "dynamic",
                "text": sc["reference_utterance"],
                "scenario_id": sc["scenario_id"],
                "viewer_intent": sc["viewer_intent"],
                "sample_type": sc["sample_type"],
                "difficulty": sc["difficulty"],
                "must_cover": sc["must_cover"],
                "failure_signals": sc["failure_signals"],
                "source_refs": sc["source_refs"],
                "source_label": content_library.SCENARIO_SOURCE_LABEL,
            }
        )
    return items
