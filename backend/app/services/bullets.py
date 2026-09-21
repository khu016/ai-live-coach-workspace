"""弹幕脚本生成（场景卡驱动）。

按时间轴生成弹幕脚本（创建练习时返回给前端，作为实时动态弹幕之外的兜底/预告）。
弹幕文本来自内容库场景卡的 ``reference_utterance``，并保留场景元数据供反馈流程回溯。

第一版实时互动主路径由 ``dynamic_bullets`` 依据稳定转写动态触发弹幕；本模块仅
生成时间轴脚本（兼容第一切片）。必考场景不再每场全量出现，而是由调用方传入
本场选定的 1–2 个 ``selected_must_ids``。

未审核内容统一以"训练场景"描述，绝不标注为"真实直播原句"。
"""

from . import content_library

# 弹幕下发节奏（秒）
FIRST_AT_SEC = 8
AT_SEC_STEP = 20
# 一次练习最多选取的场景数
MAX_SCENARIOS = 8


def build_script(live_type, goal, topic=None, seed=None, selected_must_ids=None):
    """根据直播类型与训练目标挑选场景卡，生成按时间触发的弹幕脚本。

    ``selected_must_ids``：本场选定的必考场景 ID（1–2 个）。不传时按
    ``seed``（练习 ID）确定性轮换选出。必考场景标记为 ``fixed_question``，
    其余为 ``dynamic``。
    """
    lib = content_library.get_library()
    live_type_en = content_library.LIVE_TYPE_TO_EN.get(live_type)
    if live_type_en is None:
        raise ValueError(f"不支持的直播类型：{live_type!r}")

    if selected_must_ids is None:
        selected_must_ids = content_library.select_must_cover(live_type_en, seed or 0)
    # 只保留本直播类型内的有效必考 ID
    selected_must_ids = [
        sid
        for sid in selected_must_ids
        if lib.scenarios_by_id.get(sid, {}).get("live_type") == live_type_en
    ]
    must_ids = set(selected_must_ids)

    scenarios = lib.select_scenarios(
        live_type_en,
        goal=goal,
        limit=MAX_SCENARIOS,
        seed=seed,
        must_scenario_ids=selected_must_ids,
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
