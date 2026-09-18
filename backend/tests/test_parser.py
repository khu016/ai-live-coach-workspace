import pytest

from app.services.feedback import parse_feedback


def test_valid_json():
    text = '{"issues":[{"dimension":"直播应对","start_sec":12,"end_sec":18,"evidence":"价格非常实惠","problem":"未回应追问","suggestion":"给出价格区间","retrain_target":"弹幕应答"}],"top_issue_ids":[0]}'
    fb = parse_feedback(text)
    assert len(fb.issues) == 1
    assert fb.top_issue_ids == [0]
    assert fb.issues[0].dimension == "直播应对"


def test_markdown_fence():
    text = '```json\n{"issues":[{"dimension":"表达表现","start_sec":1,"end_sec":3,"evidence":"大家好","problem":"开场平淡"}],"top_issue_ids":[0]}\n```'
    fb = parse_feedback(text)
    assert len(fb.issues) == 1


def test_bare_list():
    text = '[{"dimension":"内容质量","start_sec":0,"end_sec":5,"evidence":"很实用","problem":"缺乏依据"}]'
    fb = parse_feedback(text)
    assert len(fb.issues) == 1
    assert fb.top_issue_ids == [0]


def test_chinese_keys_and_alias():
    text = '{"issues":[{"维度":"表达","start":2,"end":6,"证据":"欢迎来到","问题":"语速太快","建议":"放慢","重练目标":"开场"}]}'
    fb = parse_feedback(text)
    assert fb.issues[0].dimension == "表达表现"
    assert fb.issues[0].evidence == "欢迎来到"


def test_unknown_dimension_raises():
    text = '{"issues":[{"dimension":"颜值","start_sec":0,"end_sec":1,"evidence":"x"}]}'
    with pytest.raises(ValueError):
        parse_feedback(text)


def test_extra_text_around_json():
    text = '好的，反馈如下：\n{"issues":[],"top_issue_ids":[]}\n以上。'
    fb = parse_feedback(text)
    assert fb.issues == []


def test_no_issues_defaults_top():
    text = '{"issues":[{"dimension":"直播应对","start_sec":0,"end_sec":1,"evidence":"a"},{"dimension":"内容质量","start_sec":1,"end_sec":2,"evidence":"b"}]}'
    fb = parse_feedback(text)
    assert fb.top_issue_ids == [0, 1]
