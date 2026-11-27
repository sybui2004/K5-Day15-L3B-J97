"""Lớp chặn đầu vào bằng NeMo Guardrails (rail `self check input`), chạy trước `agent.xu_ly`.

Thiết kế: docs/superpowers/specs/2026-11-28-nemo-guardrails-design.md.
- Model của NeMo đi qua `ai.call_model` (lớp ModelNoi), nên mỗi lần NeMo gọi model là một sự kiện `model`
  trong trace và được tính token như luồng chính.
- `nemoguardrails` chỉ được import bên trong hàm: máy chưa cài gói vẫn `import guard` được.
"""
from ai import call_model

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
