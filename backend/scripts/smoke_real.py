"""真实模型冒烟：用真实 DeepSeek 对多份示例转写生成练后反馈，供产品经理打分定 D2/D3。"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.feedback import generate_feedback  # noqa: E402

SAMPLES = [
    {
        "name": "带货·弹幕应答（价格追问未回应）",
        "live_type": "带货",
        "goal": "练习弹幕应答，回应价格与效果追问",
        "topic": "便携榨汁杯",
        "product_info": "便携榨汁杯，容量 350ml，USB 充电",
        "segments": [
            {"start": 0, "end": 6, "text": "大家好欢迎来到直播间，今天带来一款便携榨汁杯。"},
            {"start": 6, "end": 12, "text": "它很小巧，随身带着很方便。"},
            {"start": 12, "end": 18, "text": "价格方面大家放心，很实惠的。"},
            {"start": 18, "end": 24, "text": "效果嘛，反正就是好用，大家赶紧下单。"},
        ],
    },
    {
        "name": "带货·开场（开场平淡）",
        "live_type": "带货",
        "goal": "练习开场留住观众",
        "topic": "家居清洁喷雾",
        "product_info": None,
        "segments": [
            {"start": 0, "end": 5, "text": "大家好，今天给大家介绍一个产品。"},
            {"start": 5, "end": 10, "text": "就是这个清洁喷雾。"},
            {"start": 10, "end": 15, "text": "大家可以看看，需要的可以买。"},
        ],
    },
    {
        "name": "娱乐互动·冷场处理（互动不足）",
        "live_type": "娱乐互动",
        "goal": "练习冷场时主动互动",
        "topic": "聊聊周末趣事",
        "product_info": None,
        "segments": [
            {"start": 0, "end": 6, "text": "大家好啊，今天来聊聊天。"},
            {"start": 6, "end": 14, "text": "呃，也不知道聊什么。"},
            {"start": 14, "end": 22, "text": "大家有什么想说的吗？没有的话我就随便讲讲。"},
        ],
    },
    {
        "name": "知识内容·通俗度（术语太多）",
        "live_type": "知识内容",
        "goal": "把知识点讲通俗",
        "topic": "什么是复利",
        "product_info": None,
        "segments": [
            {"start": 0, "end": 6, "text": "复利就是利滚利，本金和利息一起再生息。"},
            {"start": 6, "end": 12, "text": "它的数学本质是指数增长模型。"},
            {"start": 12, "end": 20, "text": "可以用年化收益率和计息周期来推导终值公式。"},
        ],
    },
    {
        "name": "知识内容·依据（结论无依据）",
        "live_type": "知识内容",
        "goal": "练习给结论时讲依据",
        "topic": "睡眠与健康",
        "product_info": None,
        "segments": [
            {"start": 0, "end": 6, "text": "睡眠不足会严重影响健康。"},
            {"start": 6, "end": 12, "text": "这个大家都知道的。"},
            {"start": 12, "end": 18, "text": "所以一定要早睡，别熬夜。"},
        ],
    },
]


def main():
    for s in SAMPLES:
        tr = SimpleNamespace(
            live_type=s["live_type"],
            goal=s["goal"],
            topic=s.get("topic"),
            product_info=s.get("product_info"),
        )
        transcript = SimpleNamespace(segments=s["segments"])
        print("=" * 64)
        print(f"样例：{s['name']}")
        try:
            fb = generate_feedback(tr, transcript)
            print(
                json.dumps(
                    {
                        "issues": [i.model_dump() for i in fb.issues],
                        "top_issue_ids": fb.top_issue_ids,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        except Exception as e:  # noqa: BLE001
            print(f"失败：{e}")


if __name__ == "__main__":
    main()
