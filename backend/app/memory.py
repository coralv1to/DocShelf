from collections import defaultdict

_sessions: dict[str, list[dict]] = defaultdict(list)


def get_history(key: str, turns: int) -> list[dict]:
    """Lấy `turns` lượt gần nhất (mỗi lượt gồm 1 câu hỏi + 1 câu trả lời)."""
    return list(_sessions[key][-turns * 2 :])


def add_turn(key: str, question: str, answer: str) -> None:
    _sessions[key].append({"role": "user", "content": question})
    _sessions[key].append({"role": "assistant", "content": answer})


def clear(key: str) -> None:
    _sessions.pop(key, None)