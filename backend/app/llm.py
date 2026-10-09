import json
from ollama import Client

from . import config

_client = Client(host=config.OLLAMA_HOST)


def chat(messages: list[dict], json_schema: dict | None = None, temperature: float = 0.0) -> str:
    """Gửi danh sách messages cho chat model, trả về nội dung văn bản."""
    kwargs = {
        "model": config.CHAT_MODEL,
        "messages": messages,
        "options": {"temperature": temperature, "num_ctx": config.NUM_CTX},
        "think": config.THINK,
        "keep_alive": config.KEEP_ALIVE,
    }
    if json_schema is not None:
        kwargs["format"] = json_schema
    resp = _client.chat(**kwargs)
    return resp.message.content or ""


def chat_json(messages: list[dict], json_schema: dict) -> dict | None:
    """Như chat(), nhưng ép output theo JSON schema và parse thành dict."""
    raw = chat(messages, json_schema=json_schema)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None
