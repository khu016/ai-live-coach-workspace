import httpx

from ..core.config import settings


def call_chat(messages, temperature=0.3, timeout=30.0, max_retries=2) -> str:
    """调用 OpenAI 兼容的 chat/completions 接口（DeepSeek）。

    覆盖：SDK 初始化/无 Key、网络超时、限流等错误；有限重试。
    """
    if not settings.model_api_key:
        raise RuntimeError("MODEL_API_KEY 未配置")
    url = f"{settings.model_base_url}/chat/completions"
    payload = {
        "model": settings.model_name,
        "messages": messages,
        "temperature": temperature,
    }
    headers = {"Authorization": f"Bearer {settings.model_api_key}"}
    last_err = None
    for _ in range(max_retries + 1):
        try:
            resp = httpx.post(url, json=payload, headers=headers, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:  # noqa: BLE001
            last_err = e
    raise RuntimeError(f"模型调用失败: {last_err}")
