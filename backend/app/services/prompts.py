FEEDBACK_SYSTEM = """你是直播陪练教练，负责点评主播在模拟直播中的表现。

硬性边界：
- 只能依据下面提供的"场景卡"和"规则卡"评价，不得引入内容库之外的标准。
- 只评价三类表现：表达表现、直播应对、内容质量。
- 不做"能否上播"的结论；不评价眼神、表情、手势或感染力。
- 每条批评必须引用具体证据：录像时间点、触发的观众弹幕、主播原话（逐字）。
- 每次只突出最值得改进的 1-2 个问题：top_issue_ids 长度必须是 1 或 2，其值为 issues 的下标。
- 不给空泛评价（如"表现不错""需要增强感染力"）；没有发现具体问题时，issues 可以少写，不要硬凑。
- 未提供商品资料时，不得编造价格、材质、库存、功效或售后规则；相关结论一律写"当前资料无法确认"。
- 不把教学建议描述成平台官方结论，除非问题对应的 source_ref 确实存在；否则只作为训练建议表述。

事实表述必须区分三档，逐条标明：
1) 已核实事实（来自提供的资料/转写，能对应到具体内容）；
2) 主播个人表达（主播自己说出的观点或经历，不代表事实成立）；
3) AI 推断（你的分析推测，须用"推断："开头）。
资料不足时直接写"当前资料无法确认"，不得补写未提供的信息。

输出要求：只输出一个 JSON 对象，不要输出任何其他文字，不要用 markdown 代码块。
结构：
{"issues":[{"dimension":"表达表现|直播应对|内容质量","start_sec":0,"end_sec":0,"evidence":"主播原话逐字引用","trigger_bullet":"触发弹幕","scenario_id":"对应场景ID","rule_ids":["命中的规则ID"],"missed_points":["未覆盖的要点"],"problem":"问题描述","suggestion":"改进建议","retrain_target":"对应重练目标","source_refs":["内容依据来源ID"]}],"top_issue_ids":[0]}

正例：{"dimension":"直播应对","start_sec":12,"end_sec":18,"evidence":"价格非常实惠","trigger_bullet":"现在下单实际是多少钱？","scenario_id":"EC-REG-010","rule_ids":["R-REL-001"],"missed_points":["未给出具体价格"],"problem":"未回应观众对具体价格的追问","suggestion":"给出价格区间或引导到详情","retrain_target":"弹幕应答","source_refs":["SRC-DY-SCHOOL-001"]}
反例（禁止）：不要用 1.1 编号代替字段名；不要输出 issues 之外的任何解释文字。

约束：
- evidence 必须逐字引用转写原文（可截取），不得改写或编造。
- trigger_bullet 必须逐字引用"观众弹幕"中实际出现的文本；没有触发弹幕时给 null。
- scenario_id 只能从"实际出现的观众弹幕"里给出的 scenario_id 中选取；没有任何弹幕或无法对应时给 null，不得自造 ID。
- rule_ids 只能从下方"教学规则卡"中选取；没有匹配时给空数组。
- missed_points 只能从对应场景卡的 must_cover 中选取。
- source_refs 只能从对应场景卡 / 规则卡的 source_refs 中选取。
- issues 总数不超过 5 个。
"""


def _rule_lines(rules) -> list:
    lines = []
    for r in rules:
        lines.append(
            f"- {r['rule_id']} [{r.get('category', '')}] {r.get('observable_behavior', '')}；"
            f"通过条件：{r.get('pass_condition', '')}；硬性否决：{r.get('hard_fail', '')}"
        )
        refs = r.get("source_refs") or []
        if refs:
            lines.append(f"    来源：{', '.join(refs)}")
    return lines


def _get(obj, key, default=None):
    val = getattr(obj, key, None)
    if val is None and hasattr(obj, "get"):
        val = obj.get(key)
    return default if val is None else val


def _bullet_lines(bullets) -> list:
    lines = []
    for b in bullets:
        at = _get(b, "at_sec")
        text = _get(b, "text", "")
        sid = _get(b, "scenario_id", "")
        meta = _get(b, "meta") or {}
        must = meta.get("must_cover") or []
        fail = meta.get("failure_signals") or []
        line = f"[{at}] scenario_id={sid} 弹幕={text}"
        if must:
            line += f" 需覆盖={must}"
        if fail:
            line += f" 失败信号={fail}"
        lines.append(line)
    return lines


def feedback_user_prompt(training, transcript, bullets=None, rules=None) -> str:
    lines = [
        f"直播类型：{training.live_type}",
        f"训练目标：{training.goal}",
    ]
    if training.topic:
        lines.append(f"主题：{training.topic}")
    if training.product_info:
        lines.append(f"商品资料：{training.product_info}")
    else:
        lines.append(
            "商品资料：未提供。价格、材质、库存、功效、售后等商品事实一律标注"
            '"当前资料无法确认"，不得编造。'
        )
    lines.append("")
    lines.append("主播转写（带时间戳，单位秒）：")
    for seg in transcript.segments or []:
        lines.append(f"[{seg.get('start')}-{seg.get('end')}] {seg.get('text')}")
    lines.append("")
    lines.append("实际出现的观众弹幕：")
    bl = _bullet_lines(bullets or [])
    if bl:
        lines.extend(bl)
    else:
        lines.append("（无）")
    lines.append("")
    lines.append("教学规则卡：")
    rl = _rule_lines(rules or [])
    if rl:
        lines.extend(rl)
    else:
        lines.append("（无）")
    lines.append("")
    lines.append("请按上述 JSON 格式输出练后反馈。")
    return "\n".join(lines)
