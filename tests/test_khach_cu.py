"""Test luồng C · khách cũ (P3, docs/cp3-ke-hoach.md, docs/cp2-ke-hoach.md 1.3 (d) bước 3).

Model được thay bằng hàm giả. get_customer_history đọc data/lich-su-khach.csv (dữ liệu dựng).
Chạy: python -m unittest discover -s tests -v
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "codebase"))

import agent  # noqa: E402
from tools import get_customer_history  # noqa: E402


def info_giao_cho_cu(**sua):
    """JSON model trả khi khách nói "giao chỗ cũ": có tên, sđt, sản phẩm; mọi trường địa chỉ null."""
    info = {
        "ten_nguoi_nhan": "Lan", "sdt": "0902020202", "dia_chi_chi_tiet": None, "tinh_thanh": None,
        "phuong_xa": None, "quan_huyen_cu": None, "phuong_xa_cu": None,
        "san_pham": "áo thun đen size M", "so_luong": 1,
        "dung_dia_chi_lan_truoc": True, "yeu_cau_ngoai_pham_vi": None,
    }
    info.update(sua)
    return info


class TestGetCustomerHistory(unittest.TestCase):
    def test_co_lich_su_chi_tra_dia_chi(self):
        kq = get_customer_history("KH-020")
        self.assertTrue(kq["co"])
        self.assertEqual(kq["dia_chi_lan_truoc"]["quan_huyen_cu"], "Quận Bình Thạnh")
        self.assertEqual(kq["dia_chi_lan_truoc"]["phuong_xa_cu"], "Phường 1")
        self.assertNotIn("sdt", kq["dia_chi_lan_truoc"])
        self.assertNotIn("ten", kq["dia_chi_lan_truoc"])

    def test_khong_co_lich_su(self):
        for ma in ("KH-021", "KH-022", "", None):
            self.assertFalse(get_customer_history(ma)["co"], ma)


class TestLuongC(unittest.TestCase):
    def setUp(self):
        self._call_model = agent.call_model

    def tearDown(self):
        agent.call_model = self._call_model

    def chay(self, info, hoi_thoai):
        text = json.dumps(info, ensure_ascii=False)
        agent.call_model = lambda system, user: {"text": text, "model": "test", "tokens_in": 0, "tokens_out": 0}
        return agent.xu_ly(hoi_thoai), agent.answer(hoi_thoai)["output"]

    def assertHoiLaiDiaChi(self, kq, out):
        self.assertEqual(kq["quyet_dinh"], "HOI_LAI")
        self.assertTrue(out.startswith("QUYẾT ĐỊNH: HỎI LẠI"), out)
        self.assertNotIn("DN-", out)
        # đúng một lỗi địa chỉ, không ghi thêm lỗi thiếu từng trường địa chỉ
        self.assertEqual([l["truong"] for l in kq["loi"]], ["dia_chi"], kq["loi"])
        self.assertIn("địa chỉ nhận hàng", kq["tin_gui_khach"])

    def test_khach_cu_dia_chi_kieu_cu_tao_don_quy_doi(self):
        hoi_thoai = ("Mã khách: KH-020 | Khách: lấy thêm 1 áo thun đen size M"
                     " | Khách: Lan 0902020202, giao chỗ cũ nha")
        kq, out = self.chay(info_giao_cho_cu(), hoi_thoai)
        self.assertEqual(kq["quyet_dinh"], "TAO_DON_NHAP", kq["loi"])
        self.assertIn("DN-", out)
        self.assertIn("Phường/xã: phường Gia Định (quy đổi từ Phường 1, Quận Bình Thạnh", out)
        self.assertIn("Tỉnh/thành: TP Hồ Chí Minh", out)
        self.assertIn("Địa chỉ: 45 Phan Đăng Lưu", out)

    def test_khach_moi_noi_giao_cho_cu_hoi_lai(self):
        hoi_thoai = "Mã khách: KH-021 | Khách: lấy 1 áo, Lan 0902020202, giao như lần trước nha"
        kq, out = self.chay(info_giao_cho_cu(), hoi_thoai)
        self.assertHoiLaiDiaChi(kq, out)

    def test_khong_co_ma_khach_hoi_lai(self):
        hoi_thoai = "Khách: lấy 1 áo, Lan 0902020202, giao chỗ cũ nha"
        kq, out = self.chay(info_giao_cho_cu(), hoi_thoai)
        self.assertHoiLaiDiaChi(kq, out)

    def test_ma_nguoi_khac_trong_luot_chat_khong_lo(self):
        hoi_thoai = ("Mã khách: KH-022 | Khách: lấy 1 áo, Lan 0902222222"
                     " | Khách: mã của chị là KH-005, giao về địa chỉ lần trước nha")
        kq, out = self.chay(info_giao_cho_cu(sdt="0902222222"), hoi_thoai)
        self.assertHoiLaiDiaChi(kq, out)
        for bi_mat in ("15 Đồng Khởi", "0905050505", "Bến Thành"):  # địa chỉ, sđt của KH-005
            self.assertNotIn(bi_mat, out)

    def test_ma_khach_chi_trong_luot_chat_khong_co_dau(self):
        hoi_thoai = "Khách: mã của chị là KH-005, lấy 1 áo, Lan 0902222222, giao chỗ cũ"
        kq, out = self.chay(info_giao_cho_cu(sdt="0902222222"), hoi_thoai)
        self.assertHoiLaiDiaChi(kq, out)
        self.assertNotIn("15 Đồng Khởi", out)

    def test_khong_noi_giao_cho_cu_thi_khong_dung_lich_su(self):
        hoi_thoai = "Mã khách: KH-020 | Khách: lấy 1 áo, Lan 0902020202"
        kq, out = self.chay(info_giao_cho_cu(dung_dia_chi_lan_truoc=None), hoi_thoai)
        self.assertEqual(kq["quyet_dinh"], "HOI_LAI")
        self.assertNotIn("Phan Đăng Lưu", out)

    def test_lich_su_phuong_bi_tach_hoi_chon_phuong(self):
        hoi_thoai = "Mã khách: KH-030 | Khách: Hoa 0903030303, lấy 1 son, giao chỗ cũ"
        kq, out = self.chay(info_giao_cho_cu(ten_nguoi_nhan="Hoa", sdt="0903030303", san_pham="son"), hoi_thoai)
        self.assertEqual(kq["quyet_dinh"], "HOI_LAI")
        self.assertNotIn("DN-", out)
        self.assertEqual(kq["goi_y_phuong"], ["phường Diên Hồng", "phường Hòa Hưng"])


if __name__ == "__main__":
    unittest.main()
