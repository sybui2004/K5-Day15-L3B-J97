"""Test luồng dự phòng DeepSeek trong codebase/ai.py. Không gọi mạng: thay _call_claude / _call_deepseek bằng hàm giả.
Chạy: python -m unittest discover -s tests -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "codebase"))

import ai  # noqa: E402
import tracing  # noqa: E402


class LoiGia(Exception):
    """Giống lỗi của SDK anthropic: có status_code và message."""
    def __init__(self, status_code, message="lỗi"):
        super().__init__(message)
        self.status_code, self.message = status_code, message


DS = {"text": '{"ok": true}', "model": "deepseek-flash", "tokens_in": 10, "tokens_out": 2}


class TestDuPhong(unittest.TestCase):
    def setUp(self):
        self._goc = (ai.MODEL_PROVIDER, ai.FALLBACK_PROVIDER, ai.API_KEY_DEEPSEEK, ai._call_claude, ai._call_deepseek)
        ai.MODEL_PROVIDER, ai.FALLBACK_PROVIDER, ai.API_KEY_DEEPSEEK = "anthropic", "deepseek", "khoa-gia"
        ai._da_chuyen_du_phong = None
        self.goi_ds = 0

        def ds(system, user):
            self.goi_ds += 1
            return dict(DS)
        ai._call_deepseek = ds

    def tearDown(self):
        (ai.MODEL_PROVIDER, ai.FALLBACK_PROVIDER, ai.API_KEY_DEEPSEEK, ai._call_claude, ai._call_deepseek) = self._goc
        ai._da_chuyen_du_phong = None

    def _claude_loi(self, loi):
        dem = {"n": 0}

        def claude(system, user):
            dem["n"] += 1
            raise loi
        ai._call_claude = claude
        return dem

    def test_het_credit_thi_chuyen_han_sang_deepseek(self):
        dem = self._claude_loi(LoiGia(400, "Your credit balance is too low to access the Anthropic API."))
        self.assertEqual(ai.call_model("s", "u")["model"], "deepseek-flash")
        self.assertEqual(ai.call_model("s", "u")["model"], "deepseek-flash")
        self.assertEqual(dem["n"], 1)  # lần sau không thử Claude nữa
        self.assertEqual(self.goi_ds, 2)

    def test_qua_tai_chi_chuyen_lan_do(self):
        dem = self._claude_loi(LoiGia(529, "Overloaded"))
        ai.call_model("s", "u")
        ai.call_model("s", "u")
        self.assertEqual(dem["n"], 2)  # lỗi tạm thời: lần sau vẫn thử Claude trước
        self.assertEqual(self.goi_ds, 2)

    def test_loi_400_khac_khong_chuyen(self):
        self._claude_loi(LoiGia(400, "messages: field required"))
        with self.assertRaises(LoiGia):
            ai.call_model("s", "u")
        self.assertEqual(self.goi_ds, 0)

    def test_khong_bat_du_phong_thi_giu_loi_goc(self):
        ai.FALLBACK_PROVIDER = ""
        self._claude_loi(LoiGia(400, "credit balance is too low"))
        with self.assertRaises(LoiGia):
            ai.call_model("s", "u")
        self.assertEqual(self.goi_ds, 0)

    def test_thieu_key_deepseek_thi_giu_loi_goc(self):
        ai.API_KEY_DEEPSEEK = ""
        self._claude_loi(LoiGia(401, "invalid x-api-key"))
        with self.assertRaises(LoiGia):
            ai.call_model("s", "u")

    def test_claude_chay_duoc_thi_khong_goi_deepseek(self):
        ai._call_claude = lambda s, u: {"text": "{}", "model": "claude-sonnet-5-5", "tokens_in": 1, "tokens_out": 1}
        self.assertEqual(ai.call_model("s", "u")["model"], "claude-sonnet-5-5")
        self.assertEqual(self.goi_ds, 0)

    def test_trace_ghi_rieng_lan_thu_claude_va_deepseek(self):
        # review PR #60: Claude 529 rồi DeepSeek thành công → hai sự kiện model, lượt vẫn thành công
        self._claude_loi(LoiGia(529, "Overloaded"))
        tracing.begin("thu")
        ai.call_model("s", "u")
        tom_tat, su_kien = tracing.end()
        self.assertEqual(tom_tat["model_calls"], 2)
        self.assertEqual(tom_tat["errors"], [])
        model = [e for e in su_kien if e["kind"] == "model"]
        self.assertEqual([e["name"] for e in model], ["goi_claude", "goi_deepseek"])
        self.assertEqual((model[0]["tokens_in"], model[0]["tokens_out"]), (0, 0))
        self.assertEqual(model[1]["model"], "deepseek-flash")
        ghi_chu = [e["text"] for e in su_kien if e["kind"] == "note"]
        self.assertTrue(any("529" in t and "deepseek-flash" in t for t in ghi_chu), ghi_chu)

    def test_loi_khong_chuyen_van_ghi_loi_vao_trace(self):
        self._claude_loi(LoiGia(400, "messages: field required"))
        tracing.begin("thu")
        with self.assertRaises(LoiGia):
            ai.call_model("s", "u")
        tom_tat, _ = tracing.end()
        self.assertEqual(len(tom_tat["errors"]), 1)

    def test_thieu_usage_thi_bao_loi_du_lieu_do(self):
        for usage in (None, {}, {"prompt_tokens": 12}, {"completion_tokens": 5}, {"prompt_tokens": "12", "completion_tokens": 5}):
            d = {"model": "deepseek-flash", "choices": [{"message": {"content": "x"}}]}
            if usage is not None:
                d["usage"] = usage
            with self.assertRaises(ValueError, msg=usage):
                ai._doc_phan_hoi_deepseek(d)
        r = ai._doc_phan_hoi_deepseek({"model": "deepseek-flash", "choices": [{"message": {"content": ""}}],
                                       "usage": {"prompt_tokens": 0, "completion_tokens": 0}})
        self.assertEqual((r["tokens_in"], r["tokens_out"]), (0, 0))  # API thật sự trả 0 thì nhận

    def test_doc_phan_hoi_deepseek(self):
        r = ai._doc_phan_hoi_deepseek({"model": "deepseek-flash", "choices": [{"message": {"content": "xin chào"}}],
                                       "usage": {"prompt_tokens": 12, "completion_tokens": 5}})
        self.assertEqual(r, {"text": "xin chào", "model": "deepseek-flash", "tokens_in": 12, "tokens_out": 5})


if __name__ == "__main__":
    unittest.main()
