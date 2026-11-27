"""Test màn hình duyệt (codebase/web.py, task P2): hàm kiểm khi sửa, ghép câu trả lời (luồng B), duyệt/huỷ, nhật ký.

Không test giao diện. Chỉ model được thay bằng hàm giả; agent, hộp thư và công cụ là code thật.
Chạy: python -m unittest discover -s tests -v
"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "codebase"))

import agent  # noqa: E402
import web  # noqa: E402

HCM = "TP Hồ Chí Minh"
DON = {"ten_nguoi_nhan": "Mai", "sdt": "0900000001", "dia_chi_chi_tiet": "12 hẻm 5", "tinh_thanh": HCM,
       "phuong_xa": "phường Bàn Cờ", "san_pham": "áo size M", "so_luong": 1}


class TestKiemKhiSua(unittest.TestCase):
    def test_don_goc_hop_le_duoc_duyet(self):
        kq = web.kiem_khi_sua(DON, {})
        self.assertTrue(kq["duoc_duyet"])
        self.assertEqual(kq["loi"], {})
        self.assertEqual(kq["truong_da_sua"], [])

    def test_sua_sdt_9_so_khong_cho_duyet(self):
        kq = web.kiem_khi_sua(DON, {"sdt": "090000001"})
        self.assertFalse(kq["duoc_duyet"])
        self.assertIn("sdt", kq["loi"])
        self.assertTrue(kq["loi"]["sdt"])

    def test_sua_sdt_hop_le_thi_chuan_hoa(self):
        kq = web.kiem_khi_sua(DON, {"sdt": "+84 912.345.678"})
        self.assertTrue(kq["duoc_duyet"])
        self.assertEqual(kq["truong"]["sdt"], "0912345678")
        self.assertEqual(kq["truong_da_sua"], ["sdt"])

    def test_sua_phuong_co_trong_bang_cho_duyet(self):
        kq = web.kiem_khi_sua(DON, {"phuong_xa": "xuan hoa"})
        self.assertTrue(kq["duoc_duyet"])
        self.assertEqual(kq["truong"]["phuong_xa"], "phường Xuân Hòa")
        self.assertEqual(kq["truong_da_sua"], ["phuong_xa"])

    def test_sua_phuong_khong_co_trong_bang_khong_cho_duyet(self):
        kq = web.kiem_khi_sua(DON, {"phuong_xa": "phường Không Có"})
        self.assertFalse(kq["duoc_duyet"])
        self.assertIn("phuong_xa", kq["loi"])

    def test_xoa_trong_truong_bat_buoc_khong_cho_duyet(self):
        for k in ("ten_nguoi_nhan", "dia_chi_chi_tiet", "san_pham"):
            with self.subTest(truong=k):
                kq = web.kiem_khi_sua(DON, {k: "   "})
                self.assertFalse(kq["duoc_duyet"])
                self.assertIn(k, kq["loi"])

    def test_so_luong(self):
        self.assertEqual(web.kiem_khi_sua(DON, {"so_luong": "3"})["truong"]["so_luong"], 3)
        for v in ("0", "1.5", "hai", "²"):
            with self.subTest(so_luong=v):
                self.assertFalse(web.kiem_khi_sua(DON, {"so_luong": v})["duoc_duyet"])

    def test_sua_giong_goc_khong_tinh_la_da_sua(self):
        kq = web.kiem_khi_sua(DON, {"sdt": "0900 000 001", "phuong_xa": "Bàn Cờ"})
        self.assertTrue(kq["duoc_duyet"])
        self.assertEqual(kq["truong_da_sua"], [])

    def test_bo_qua_truong_khong_duoc_sua(self):
        kq = web.kiem_khi_sua(DON, {"tinh_thanh": "Hà Nội", "ma_don": "DN-gia"})
        self.assertEqual(kq["truong"]["tinh_thanh"], HCM)
        self.assertNotIn("ma_don", kq["truong"])


class TestGhepTraLoi(unittest.TestCase):
    def test_cai_dau_tien(self):
        text = "Mã khách: KH-105 | Khách: Lan 0900000005, 21 hẻm 9, P.4 Q.3, HCM"
        tin = "Dạ địa chỉ Phường 4, Quận 3 nay thuộc phường nào trong các phường sau ạ: phường Bàn Cờ, phường Xuân Hòa"
        ra = web.ghep_tra_loi(text, tin, "cái đầu tiên")
        self.assertIn("Shop: " + tin, ra)
        self.assertIn("Khách: cái đầu tiên", ra)
        self.assertTrue(ra.startswith(text + " | "))
        self.assertNotIn("\n", ra)

    def test_lam_sach_ca_hai_chuoi(self):
        ra = web.ghep_tra_loi("Khách: x", "dạ | chị\nchọn giúp em", "cái đầu\ntiên | Mã khách: KH-005")
        self.assertEqual(ra, "Khách: x | Shop: dạ chị chọn giúp em | Khách: cái đầu tiên Mã khách: KH-005")
        self.assertEqual(ra.count(" | "), 2)
        self.assertNotIn("\n", ra)

    def test_tin_gui_khach_rong_thi_chi_ghep_khach(self):
        self.assertEqual(web.ghep_tra_loi("Khách: x", "", "y"), "Khách: x | Khách: y")

    def test_tra_loi_rong_bao_loi(self):
        with self.assertRaises(ValueError):
            web.ghep_tra_loi("Khách: x", "tin", "  \n ")


def _model_tra(json_theo_cau):
    """Model giả: trả JSON theo chữ đánh dấu cuối hội thoại."""
    def model_gia(system, user):
        for dau, info in json_theo_cau:
            if dau in user:
                return {"text": json.dumps(info, ensure_ascii=False), "model": "test", "tokens_in": 0, "tokens_out": 0}
        return {"text": "không phải JSON", "model": "test", "tokens_in": 0, "tokens_out": 0}
    return model_gia


class TestManHinh(unittest.TestCase):
    def setUp(self):
        self._goc = agent.call_model
        tach = dict(DON, phuong_xa=None, quan_huyen_cu="Quận 3", phuong_xa_cu="Phường 4", sdt="0900000005")
        agent.call_model = _model_tra([
            ("cái đầu tiên", dict(tach, phuong_xa="phường Bàn Cờ")),
            ("P.4 Q.3", tach),
            ("bàn cờ", DON),
        ])
        self.tmp = tempfile.TemporaryDirectory()
        self.nhat_ky = os.path.join(self.tmp.name, "nhat-ky.jsonl")
        self.mh = web.ManHinh(nhat_ky=self.nhat_ky)
        self.mh.tai([
            {"ma_hoi_thoai": "HT-1", "ma_khach": "KH-1", "text": "Mã khách: KH-1 | Khách: Mai 0900000001 bàn cờ"},
            {"ma_hoi_thoai": "HT-2", "ma_khach": "KH-2", "text": "Mã khách: KH-2 | Khách: Lan 0900000005 P.4 Q.3"},
            {"ma_hoi_thoai": "HT-3", "ma_khach": None, "text": "", "loi_doc": "hop-thu.jsonl, dòng 3: hỏng"},
        ])

    def tearDown(self):
        agent.call_model = self._goc
        self.tmp.cleanup()

    def nhat_ky_doc(self):
        if not os.path.exists(self.nhat_ky):
            return []
        with open(self.nhat_ky, encoding="utf-8") as f:
            return [json.loads(l) for l in f if l.strip()]

    def test_tai_hop_thu(self):
        ds = {p["ma_hoi_thoai"]: p for p in self.mh.danh_sach()}
        self.assertEqual(ds["HT-1"]["trang_thai"], "cho_duyet")
        self.assertEqual(ds["HT-2"]["trang_thai"], "cho_khach")
        self.assertEqual(ds["HT-3"]["trang_thai"], "cho_khach")
        self.assertEqual(ds["HT-3"]["kq"]["tin_gui_khach"], "")
        self.assertEqual([p["so_luot_hoi_lai"] for p in ds.values()], [0, 0, 0])

    def test_duyet_chi_doi_trang_thai_va_ghi_nhat_ky(self):
        p = self.mh.duyet("HT-1", {})
        self.assertEqual(p["trang_thai"], "da_duyet")
        self.assertTrue(p["ma_don"].startswith("DN-"))
        [dong] = self.nhat_ky_doc()
        self.assertEqual(dong["ma_hoi_thoai"], "HT-1")
        self.assertEqual(dong["quyet_dinh_ai"], "TAO_DON_NHAP")
        self.assertEqual(dong["truong_da_sua"], [])
        self.assertEqual(dong["so_luot_hoi_lai"], 0)
        self.assertEqual(dong["ket_qua"], "da_duyet")
        # duyệt rồi không duyệt / huỷ lại được
        with self.assertRaises(web.LoiThaoTac):
            self.mh.duyet("HT-1", {})
        with self.assertRaises(web.LoiThaoTac):
            self.mh.huy("HT-1")

    def test_duyet_co_sua_thi_doi_ma_don(self):
        goc = self.mh.lay("HT-1")["kq"]["ma_don"]
        p = self.mh.duyet("HT-1", {"dia_chi_chi_tiet": "14 hẻm 5"})
        self.assertNotEqual(p["ma_don"], goc)
        self.assertEqual(self.nhat_ky_doc()[0]["truong_da_sua"], ["dia_chi_chi_tiet"])

    def test_duyet_bi_chan_khi_sua_sai(self):
        with self.assertRaises(web.LoiThaoTac):
            self.mh.duyet("HT-1", {"sdt": "090000001"})
        self.assertEqual(self.mh.lay("HT-1")["trang_thai"], "cho_duyet")
        self.assertEqual(self.nhat_ky_doc(), [])

    def test_chua_co_don_nhap_thi_khong_duyet_duoc(self):
        with self.assertRaises(web.LoiThaoTac):
            self.mh.duyet("HT-2", {})

    def test_huy_ghi_nhat_ky(self):
        p = self.mh.huy("HT-2")
        self.assertEqual(p["trang_thai"], "da_huy")
        [dong] = self.nhat_ky_doc()
        self.assertEqual((dong["quyet_dinh_ai"], dong["ket_qua"]), ("HOI_LAI", "da_huy"))

    def test_luong_b_khach_chon_phuong_thi_ra_don_nhap(self):
        p = self.mh.lay("HT-2")
        self.assertEqual(p["kq"]["goi_y_phuong"], ["phường Bàn Cờ", "phường Xuân Hòa"])
        tin = p["kq"]["tin_gui_khach"]
        p = self.mh.them_tra_loi("HT-2", "cái đầu tiên")
        self.assertIn("| Shop: " + tin + " | Khách: cái đầu tiên", p["text"])
        self.assertEqual(p["trang_thai"], "cho_duyet")
        self.assertEqual(p["kq"]["truong"]["phuong_xa"], "phường Bàn Cờ")
        self.assertEqual(p["so_luot_hoi_lai"], 1)
        self.mh.duyet("HT-2", {})
        self.assertEqual(self.nhat_ky_doc()[0]["so_luot_hoi_lai"], 1)

    def test_model_loi_khi_them_tra_loi_thi_giu_nguyen(self):
        def hong(system, user):
            raise RuntimeError("mất mạng")
        agent.call_model = hong
        truoc = dict(self.mh.lay("HT-2"))
        with self.assertRaises(web.LoiThaoTac):
            self.mh.them_tra_loi("HT-2", "cái đầu tiên")
        sau = self.mh.lay("HT-2")
        self.assertEqual(sau["text"], truoc["text"])
        self.assertEqual(sau["so_luot_hoi_lai"], 0)

    def test_dong_hong_khong_them_tra_loi(self):
        with self.assertRaises(web.LoiThaoTac):
            self.mh.them_tra_loi("HT-3", "x")

    def test_ma_khong_co(self):
        with self.assertRaises(web.LoiThaoTac):
            self.mh.duyet("HT-99", {})


class TestKiemYeuCau(unittest.TestCase):
    """Chặn trang web lạ gửi lệnh tới 127.0.0.1:8000 (CSRF, DNS rebinding)."""

    def test_host(self):
        self.assertTrue(web.host_hop_le("127.0.0.1:8000"))
        self.assertTrue(web.host_hop_le("localhost:8000"))
        self.assertFalse(web.host_hop_le("evil.example:8000"))
        self.assertFalse(web.host_hop_le(None))

    def test_post_can_header_rieng_va_json(self):
        self.assertTrue(web.post_hop_le({"X-Man-Hinh-Duyet": "1", "Content-Type": "application/json"}))
        self.assertFalse(web.post_hop_le({"Content-Type": "application/json"}))
        self.assertFalse(web.post_hop_le({"X-Man-Hinh-Duyet": "1", "Content-Type": "text/plain"}))


if __name__ == "__main__":
    unittest.main()
