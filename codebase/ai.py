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
import json
import os
import sys
import urllib.error
import urllib.request

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
# Dự phòng khi Claude không gọi được (hết credit, sai key, quá tải, mất mạng): gọi DeepSeek.
# Có API_KEY_DEEPSEEK thì tự bật; FALLBACK_PROVIDER=tat để tắt.
API_KEY_DEEPSEEK = (os.environ.get("API_KEY_DEEPSEEK") or "").strip()
FALLBACK_PROVIDER = (os.environ.get("FALLBACK_PROVIDER") or ("deepseek" if API_KEY_DEEPSEEK else "")).strip().lower()
FALLBACK_MODEL = (os.environ.get("FALLBACK_MODEL") or "deepseek-flash").strip()  # DeepSeek V4.1 Flash
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
_da_chuyen_du_phong = None  # lý do đã chuyển hẳn sang dự phòng (hết credit / sai key) trong tiến trình này

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


def _doc_phan_hoi_deepseek(d: dict) -> dict:
    """Phản hồi chat/completions (chuẩn OpenAI) → hợp đồng call_model. completion_tokens đã gồm token suy luận."""
    u = d.get("usage") or {}
    return {"text": ((d.get("choices") or [{}])[0].get("message") or {}).get("content") or "",
            "model": d.get("model") or FALLBACK_MODEL, "tokens_in": int(u.get("prompt_tokens") or 0),
            "tokens_out": int(u.get("completion_tokens") or 0)}


def _call_deepseek(system: str, user: str) -> dict:
    """Gọi DeepSeek (API chuẩn OpenAI) bằng urllib, không thêm thư viện. Key: API_KEY_DEEPSEEK trong .env."""
    body = json.dumps({"model": FALLBACK_MODEL, "max_tokens": 8000, "stream": False,
                       "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}).encode()
    req = urllib.request.Request(DEEPSEEK_URL, data=body, method="POST", headers={
        "Content-Type": "application/json", "Authorization": "Bearer " + API_KEY_DEEPSEEK})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return _doc_phan_hoi_deepseek(json.loads(r.read().decode("utf-8")))
    except urllib.error.HTTPError as e:
        raise RuntimeError("DeepSeek HTTP %s: %s" % (e.code, e.read().decode("utf-8", "replace")[:300])) from e


def _loai_loi_claude(e):
    """'han' = lỗi kéo dài cả phiên (hết credit, sai key, bị chặn quyền) → chuyển hẳn sang dự phòng.
    'tam' = lỗi tạm thời (quá tải, giới hạn lượt, lỗi máy chủ, mất mạng) → chỉ chuyển lần gọi này.
    None = lỗi do yêu cầu (vd 400 thiếu trường): không chuyển, để lỗi bay ra như cũ."""
    ma = getattr(e, "status_code", None)
    loi = str(getattr(e, "message", "") or e).lower()
    if ma in (401, 402, 403) or (ma == 400 and ("credit" in loi or "billing" in loi)):
        return "han"
    if ma in (408, 409, 429) or (isinstance(ma, int) and ma >= 500):
        return "tam"
    if ma is None and type(e).__name__ in ("APIConnectionError", "APITimeoutError"):
        return "tam"
    return None


def _co_du_phong():
    return FALLBACK_PROVIDER == "deepseek" and bool(API_KEY_DEEPSEEK)


@model_call
def call_model(system: str, user: str) -> dict:
    if MODEL_PROVIDER == "fake":
        last = (user.strip().splitlines() or [""])[-1]
        return {"text": "[câu trả lời giả — chưa nối model] " + last[:60], "model": "fake", "tokens_in": 0, "tokens_out": 0}

    if MODEL_PROVIDER == "deepseek":
        return _call_deepseek(system, user)

    if MODEL_PROVIDER == "anthropic":
        global _da_chuyen_du_phong
        if _da_chuyen_du_phong and _co_du_phong():
            return _call_deepseek(system, user)
        try:
            return _call_claude(system, user)
        except Exception as e:  # noqa: BLE001 — chỉ chuyển với lỗi _loai_loi_claude nhận ra
            loai = _loai_loi_claude(e)
            if loai is None or not _co_du_phong():
                raise
            if loai == "han":
                _da_chuyen_du_phong = "%s: %s" % (type(e).__name__, e)
            print("   [dự phòng] Claude lỗi (%s: %s) → gọi %s%s" % (type(e).__name__, str(e)[:120], FALLBACK_MODEL,
                  " cho các lần sau" if loai == "han" else ""), file=sys.stderr)
            return _call_deepseek(system, user)
    raise NotImplementedError(
        "chưa viết phần gọi model thật cho MODEL_PROVIDER=%s trong codebase/ai.py — xem docs/connect-model.md"
        % MODEL_PROVIDER)
