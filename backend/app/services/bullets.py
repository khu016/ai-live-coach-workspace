"""弹幕脚本生成。

本切片为确定性模板：预设关键问题 + 主题/通用互动弹幕池，按时间轴下发。
"弹幕随主播发言实时变化"依赖流式 ASR，后置实现，此处不冒充。
"""

FIXED_QUESTIONS = {
    "带货": [
        "这款产品的核心卖点是什么？",
        "价格多少？有优惠吗？",
        "有没有用过的人反馈？",
    ],
    "娱乐互动": [
        "主播能和大家聊点开心的吗？",
        "有什么才艺展示一下？",
        "最近有什么好玩的事分享？",
    ],
    "知识内容": [
        "这个知识点能再讲得通俗一点吗？",
        "这个结论的依据是什么？",
        "有没有常见的误区？",
    ],
}

GENERIC_BULLETS = [
    "讲得不错，继续！",
    "能再具体一点吗？",
    "新来的，主播在聊什么？",
    "这里没太听懂。",
    "主播加油！",
]


def _template_bullets(topic):
    if topic:
        return [
            f"能再展开讲讲「{topic}」吗？",
            f"关于「{topic}」，观众最关心什么？",
            f"「{topic}」这里有什么坑吗？",
            "讲得不错，继续！",
            "能举个具体例子吗？",
        ]
    return list(GENERIC_BULLETS)


def build_script(live_type, goal, topic):
    items = []
    fixed = FIXED_QUESTIONS.get(live_type, [])
    for i, q in enumerate(fixed[:3]):
        items.append({"at_sec": 8 + i * 25, "kind": "fixed_question", "text": q})
    for i, b in enumerate(_template_bullets(topic)[:5]):
        items.append({"at_sec": 15 + i * 18, "kind": "dynamic", "text": b})
    items.sort(key=lambda x: x["at_sec"])
    return items
