"""Lớp chặn đầu vào bằng NeMo Guardrails (rail `self check input`), chạy trước `agent.xu_ly`.

Thiết kế: docs/superpowers/specs/2026-11-28-nemo-guardrails-design.md.
- Model của NeMo đi qua `ai.call_model` (lớp ModelNoi), nên mỗi lần NeMo gọi model là một sự kiện `model`
  trong trace và được tính token như luồng chính.
- `nemoguardrails` chỉ được import bên trong hàm: máy chưa cài gói vẫn `import guard` được.
"""
import logging
import os
import re
import warnings

from ai import call_model

CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "guard_config")

SYSTEM_MAC_DINH = "Bạn là bộ kiểm tra tin nhắn đầu vào của shop. Chỉ trả lời đúng một từ tiếng Anh: Yes hoặc No."


def _vai(msg) -> str:
    role = getattr(msg, "role", "")
    return str(getattr(role, "value", role))


class ModelNoi:
    """Model cho NeMo theo giao thức `nemoguardrails.types.LLMModel` (0.25), gọi `call_model(system, user)`."""

    model_name = "call_model"
    provider_name = "j97"
    provider_url = None

    def _goi(self, prompt):
        if isinstance(prompt, str):
            system, user = SYSTEM_MAC_DINH, prompt
        else:
            system = "\n".join(str(m.content or "") for m in prompt if _vai(m) == "system") or SYSTEM_MAC_DINH
            user = "\n".join("%s: %s" % (_vai(m), m.content or "") for m in prompt if _vai(m) != "system")
        return call_model(system, user)

    async def generate_async(self, prompt, *, stop=None, **kwargs):
        from nemoguardrails.types import LLMResponse
        r = self._goi(prompt)
        return LLMResponse(content=r.get("text") or "", model=r.get("model"))

    async def stream_async(self, prompt, *, stop=None, **kwargs):
        from nemoguardrails.types import LLMResponseChunk
        r = self._goi(prompt)
        yield LLMResponseChunk(delta_content=r.get("text") or "", model=r.get("model"))


def _loi_khach(text: str) -> str:
    """Chỉ lấy lời khách: các lượt `Khách:` (tách theo ` | `), mỗi lượt một dòng. Bỏ dòng `Mã khách` và lượt
    `Shop:` thật, để guard không coi tin thật của shop là khách giả lời shop (spec mục 6).
    Không có lượt `Khách:` nào thì trả nguyên chuỗi, để không bỏ sót."""
    luot = [p.strip() for p in str(text).split("|") if re.match(r"\s*Khách\s*:", p)]
    return "\n".join(luot) if luot else str(text)


def tra_loi_chan(output) -> list:
    """Đọc câu trả lời của `self_check_input`: [True] là cho qua, [False] là chặn.
    Chữ đầu là "yes" (hoa/thường, có dấu chấm hay khoảng trắng) thì chặn; "No" hay trả lời mơ hồ thì cho qua,
    vì bước 2 và các lớp kiểm của code vẫn chặn phía sau."""
    dau = re.sub(r"\W+", " ", str(output or "")).strip().lower().split(" ")[0]
    return [dau != "yes"]


_RAILS = None


def _rails():
    """Dựng LLMRails một lần cho cả tiến trình (hộp thư 10 hội thoại không dựng lại mỗi câu)."""
    global _RAILS
    if _RAILS is None:
        from nemoguardrails import LLMRails, RailsConfig
        # NeMo tự in traceback khi model lỗi; lỗi đã nằm trong `loi` và trace (agent.py note), nên tắt bớt.
        logging.getLogger("nemoguardrails").setLevel(logging.CRITICAL)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # NeMo cảnh báo LLMRails sẽ bị thay bằng Guardrails
            rails = LLMRails(RailsConfig.from_path(CONFIG), llm=ModelNoi())
        rails.register_output_parser(tra_loi_chan, "tra_loi_chan")
        _RAILS = rails
    return _RAILS


def kiem_dau_vao(text: str) -> dict:
    """Chạy rail `self check input` trên lời khách. Lỗi bất kỳ (thiếu gói, mạng, model) thì cho qua và ghi `loi`."""
    try:
        from nemoguardrails.rails.llm.options import RailStatus, RailType
        kq = _rails().check([{"role": "user", "content": _loi_khach(text)}], rail_types=[RailType.INPUT])
        if kq.status == RailStatus.BLOCKED:
            return {"chan": True, "ly_do": "self check input", "loi": None}
        return {"chan": False, "ly_do": "", "loi": None}
    except Exception as e:  # noqa: BLE001 — fail-open có chủ ý (spec mục 6)
        return {"chan": False, "ly_do": "", "loi": "%s: %s" % (type(e).__name__, e)}
