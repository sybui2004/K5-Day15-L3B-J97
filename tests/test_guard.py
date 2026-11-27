"""Test lớp chặn đầu vào codebase/guard.py (NeMo Guardrails, docs/superpowers/plans/2026-11-28-nemo-guardrails.md).

Model được thay bằng hàm giả, không gọi mạng. Test cần `nemoguardrails` thì bỏ qua khi máy chưa cài gói.
Chạy: python -m unittest discover -s tests -p "test_guard.py" -v
"""
import asyncio
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "codebase"))

import guard  # noqa: E402

try:
    from nemoguardrails.types import ChatMessage
    CO_NEMO = True
except ImportError:
    CO_NEMO = False


class ModelGia:
    """Thay guard.call_model: ghi lại (system, user), trả lần lượt các câu trong `tra`."""

    def __init__(self, *tra):
        self.goi = []
        self.tra = list(tra) or ["No"]

    def __call__(self, system, user):
        self.goi.append((system, user))
        text = self.tra[min(len(self.goi), len(self.tra)) - 1]
        if isinstance(text, Exception):
            raise text
        return {"text": text, "model": "gia", "tokens_in": 3, "tokens_out": 1}


@unittest.skipUnless(CO_NEMO, "chưa cài nemoguardrails")
class TestModelNoi(unittest.TestCase):
    def setUp(self):
        self.model = ModelGia()
        self._cu = guard.call_model
        guard.call_model = self.model

    def tearDown(self):
        guard.call_model = self._cu

    def test_chuoi_thanh_user_va_system_mac_dinh(self):
        r = asyncio.run(guard.ModelNoi().generate_async("kiểm tin này"))
        self.assertEqual(self.model.goi, [(guard.SYSTEM_MAC_DINH, "kiểm tin này")])
        self.assertEqual(r.content, "No")

    def test_danh_sach_tach_system_va_phan_con_lai(self):
        msgs = [ChatMessage.from_system("luật"), ChatMessage.from_user("tin khách")]
        asyncio.run(guard.ModelNoi().generate_async(msgs))
        self.assertEqual(self.model.goi[0][0], "luật")
        self.assertIn("tin khách", self.model.goi[0][1])

    def test_moi_lan_goi_mot_lan_call_model(self):
        asyncio.run(guard.ModelNoi().generate_async("a"))
        asyncio.run(guard.ModelNoi().generate_async("b"))
        self.assertEqual(len(self.model.goi), 2)

    def test_stream_tra_mot_chunk(self):
        async def gom():
            return [c async for c in guard.ModelNoi().stream_async("a")]
        chunks = asyncio.run(gom())
        self.assertEqual([c.delta_content for c in chunks], ["No"])


if __name__ == "__main__":
    unittest.main()
