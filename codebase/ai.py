"""Nối model — chỗ DUY NHẤT trong bản chạy thử gọi model AI. NHÓM VIẾT phần gọi model thật.

Hợp đồng (giữ nguyên để khung đo được token):
    call_model(system: str, user: str) -> dict với 4 khoá
        "text":       str   chữ model trả về
        "model":      str   tên model đã gọi (để tra giá ở bảng giá model)
        "tokens_in":  int   số token vào, lấy từ trường usage trong phản hồi API — KHÔNG ước lượng
        "tokens_out": int   số token ra, gồm cả token suy luận / suy nghĩ nếu API tính riêng
    @model_call (từ tracing.py) tự ghi mỗi lần gọi vào trace; agent.py gọi call_model bao nhiêu lần
    cũng được, khung tự cộng token.
    Lỗi gọi model (hết lượt, sai key, mất mạng): cứ để exception bay ra — khung ghi lỗi vào cột error.

Chế độ giả (mặc định khi .env chưa có MODEL_PROVIDER, hoặc MODEL_PROVIDER=fake):
    trả một câu giả cố định, model "fake", token 0 — để luồng chạy hết từ trước CP2 (guide bước 3.2).
    Lượt `run.py eval` / `run.py simulate` chạy bằng model giả KHÔNG được tính.

Nối model thật: điền .env (chép từ .env.example), rồi viết nhánh gọi API ở dưới theo docs/connect-model.md
(có ví dụ OpenAI, Claude, model chạy trên máy, và cách nối nhà cung cấp khác). Không dán API key vào file này.
"""
import os

from tracing import model_call

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_env(path=os.path.join(ROOT, ".env")):
    """Đọc file .env (KEY=VALUE mỗi dòng) vào biến môi trường, không ghi đè biến đã có. Khung — không cần sửa."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env()
MODEL_PROVIDER = (os.environ.get("MODEL_PROVIDER") or "fake").strip().lower()
MODEL_NAME = (os.environ.get("MODEL_NAME") or "").strip()
API_KEY = (os.environ.get("API_KEY") or "").strip()
MODEL_EFFORT = (os.environ.get("MODEL_EFFORT") or "").strip().lower()  # low | medium | high | xhigh | max

_claude = None  # client Anthropic, tạo một lần khi gọi lần đầu


def _call_claude(system: str, user: str) -> dict:
    """Gọi Claude qua SDK chính thức `anthropic` (requirements.txt).

    - Thinking để mặc định (adaptive); độ sâu chỉnh bằng MODEL_EFFORT trong .env.
    - fallbacks="default": khi bộ lọc an toàn từ chối, API tự chạy lại trên model dự phòng trong cùng lần gọi.
    - Bị từ chối hẳn (stop_reason "refusal") thì trả text rỗng → agent.py coi là JSON hỏng → HỎI LẠI.
    """
    global _claude
    import anthropic
    if _claude is None:
        _claude = anthropic.Anthropic(api_key=API_KEY or None)
    kwargs = {
        "model": MODEL_NAME or "claude-sonnet-5-5",
        "max_tokens": 16000,
        "system": system,
        "messages": [{"role": "user", "content": user}],
        "betas": ["server-side-fallback-2026-07-01"],
        "fallbacks": "default",
    }
    if MODEL_EFFORT:
        kwargs["output_config"] = {"effort": MODEL_EFFORT}
    resp = _claude.beta.messages.create(**kwargs)
    text = "" if resp.stop_reason == "refusal" else "".join(b.text for b in resp.content if b.type == "text")
    return {"text": text, "model": resp.model, "tokens_in": resp.usage.input_tokens,
            "tokens_out": resp.usage.output_tokens}


@model_call
def call_model(system: str, user: str) -> dict:
    if MODEL_PROVIDER == "fake":
        last = (user.strip().splitlines() or [""])[-1]
        return {"text": "[câu trả lời giả — chưa nối model] " + last[:60], "model": "fake", "tokens_in": 0, "tokens_out": 0}

    if MODEL_PROVIDER == "anthropic":
        return _call_claude(system, user)
    raise NotImplementedError(
        "chưa viết phần gọi model thật cho MODEL_PROVIDER=%s trong codebase/ai.py — xem docs/connect-model.md"
        % MODEL_PROVIDER)
