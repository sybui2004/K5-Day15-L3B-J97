"""Test bốn công cụ X2 (codebase/tools.py). Chạy: python -m unittest discover -s tests -v

Tên phường lấy từ data/chuyen-doi-dia-gioi.csv (X0, Nghị quyết 1685/NQ-UBTVQH15).
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "codebase"))

from tools import validate_phone, convert_old_address, lookup_address, create_draft_order  # noqa: E402

HCM = "TP Hồ Chí Minh"


class TestValidatePhone(unittest.TestCase):
    def test_co_dau_cach(self):
        kq = validate_phone("0912 345 678")
        self.assertTrue(kq["ok"])
        self.assertEqual(kq["sdt_chuan"], "0912345678")

    def test_dau_84_va_dau_cham(self):
        self.assertEqual(validate_phone("+84 912.345.678")["sdt_chuan"], "0912345678")

    def test_84_khong_dau_cong(self):
        self.assertEqual(validate_phone("84912345678")["sdt_chuan"], "0912345678")

    def test_9_so(self):
        kq = validate_phone("091234567")
        self.assertFalse(kq["ok"])
        self.assertTrue(kq["ly_do"])

    def test_dau_02(self):
        self.assertFalse(validate_phone("0212345678")["ok"])

    def test_rong_hoac_co_chu(self):
        self.assertFalse(validate_phone("")["ok"])
        self.assertFalse(validate_phone(None)["ok"])
        self.assertFalse(validate_phone("09123abc78")["ok"])

    def test_chu_so_khong_phai_ascii(self):
        # str.isdigit() coi '²', '０' (toàn khổ), '٣' là chữ số; số gọi được chỉ có 0-9
        for s in ["09" + "²" * 8, "０９１２３４５６７８", "091234567٣"]:
            with self.subTest(sdt=s):
                kq = validate_phone(s)
                self.assertFalse(kq["ok"])
                self.assertIsNone(kq["sdt_chuan"])


class TestConvertOldAddress(unittest.TestCase):
    def test_gop_gon_quan_viet_tat(self):
        # khoản 7: Phường 9, 11, 12, 14 (Quận 3) -> phường Nhiêu Lộc
        kq = convert_old_address(HCM, "q3", "Phường 9")
        self.assertEqual(kq["ket_qua"], "mot")
        self.assertEqual(kq["phuong_moi"], ["phường Nhiêu Lộc"])
        self.assertEqual(kq["tinh_moi"], HCM)
        self.assertEqual(kq["khoan"], [7])

    def test_bi_tach(self):
        # khoản 5, 6: Phường 4 (Quận 3) -> một phần Bàn Cờ, phần còn lại Xuân Hòa
        kq = convert_old_address("tp hcm", "Quận 3", "P.4")
        self.assertEqual(kq["ket_qua"], "nhieu")
        self.assertGreaterEqual(len(kq["phuong_moi"]), 2)
        self.assertEqual(set(kq["phuong_moi"]), {"phường Bàn Cờ", "phường Xuân Hòa"})
        self.assertEqual(kq["khoan"], [5, 6])

    def test_khong_thay(self):
        kq = convert_old_address(HCM, "Quận 3", "Phường 99")
        self.assertEqual(kq["ket_qua"], "khong_thay")
        self.assertEqual(kq["phuong_moi"], [])
        self.assertIsNone(kq["tinh_moi"])

    def test_cung_ten_phuong_khac_quan(self):
        # Phường 1 có ở nhiều quận: Quận 3 -> Bàn Cờ (khoản 5), Quận 4 -> Vĩnh Hội (khoản 10)
        self.assertEqual(convert_old_address(HCM, "Quận 3", "Phường 1")["phuong_moi"], ["phường Bàn Cờ"])
        self.assertEqual(convert_old_address(HCM, "Quận 4", "Phường 1")["phuong_moi"], ["phường Vĩnh Hội"])

    def test_so_co_so_0_va_dau_cham(self):
        # khoản 26: Phường 1 (Quận 10) -> phường Vườn Lài
        self.assertEqual(convert_old_address("hcm", "q.10", "p.01")["phuong_moi"], ["phường Vườn Lài"])

    def test_ten_bat_dau_bang_chu_p(self):
        # khoản 54, 55: Phường 15 (quận Phú Nhuận) bị tách -> Cầu Kiệu, Phú Nhuận; "Phú" không bị cắt chữ P
        kq = convert_old_address(HCM, "quận Phú Nhuận", "Phường 15")
        self.assertEqual(kq["ket_qua"], "nhieu")
        self.assertEqual(set(kq["phuong_moi"]), {"phường Cầu Kiệu", "phường Phú Nhuận"})
        self.assertEqual(convert_old_address(HCM, "Phu Nhuan", "phuong 8")["phuong_moi"], ["phường Phú Nhuận"])

    def test_tinh_cu_binh_duong(self):
        # khoản 85: phường An Thạnh (thành phố Thuận An) -> phường Thuận An
        kq = convert_old_address("Bình Dương", "thành phố Thuận An", "phường An Thạnh")
        self.assertEqual(kq["ket_qua"], "mot")
        self.assertEqual(kq["phuong_moi"], ["phường Thuận An"])
        self.assertEqual(kq["tinh_moi"], HCM)
        self.assertTrue(kq["khoan"])

    def test_tinh_cu_vung_tau_viet_tat(self):
        # khoản 102: Phường 1 (thành phố Vũng Tàu) -> phường Vũng Tàu
        kq = convert_old_address("brvt", "tp Vũng Tàu", "Phường 1")
        self.assertEqual(kq["phuong_moi"], ["phường Vũng Tàu"])
        self.assertEqual(kq["tinh_moi"], HCM)

    def test_tinh_cu_khong_khop_quan(self):
        # Quận 3 thuộc TP HCM cũ, không thuộc Bình Dương
        self.assertEqual(convert_old_address("Bình Dương", "Quận 3", "Phường 9")["ket_qua"], "khong_thay")

    def test_ngoai_pham_vi(self):
        self.assertEqual(convert_old_address("Hà Nội", "quận Hoàn Kiếm", "phường Hàng Bạc")["ket_qua"], "khong_thay")

    def test_chu_so_khong_phai_ascii_khong_lam_dung(self):
        # '²'.isdigit() là True nhưng int('²') lỗi: không được ném ngoại lệ, chỉ trả khong_thay
        for phuong in ["Phường ²", "Phường ０７", "p.²"]:
            with self.subTest(phuong=phuong):
                kq = convert_old_address("hcm", "Quận 3", phuong)
                self.assertEqual(kq["ket_qua"], "khong_thay")
                self.assertTrue(kq["ly_do"])
        self.assertEqual(convert_old_address("hcm", "Quận ³", "Phường 9")["ket_qua"], "khong_thay")

    def test_ca_huyen_con_dao(self):
        # khoản 163: cả huyện Côn Đảo -> đặc khu Côn Đảo; huyện không có phường/xã nên phường cũ để trống là hợp lệ
        for phuong in ["", None, "Côn Đảo"]:
            with self.subTest(phuong=phuong):
                kq = convert_old_address("brvt", "Côn Đảo", phuong)
                self.assertEqual(kq["ket_qua"], "mot")
                self.assertEqual(kq["phuong_moi"], ["đặc khu Côn Đảo"])
                self.assertEqual(kq["khoan"], [163])

    def test_ca_huyen_ten_phuong_mau_thuan(self):
        kq = convert_old_address("brvt", "huyện Côn Đảo", "Phường 99")
        self.assertEqual(kq["ket_qua"], "khong_thay")
        self.assertTrue(kq["ly_do"])

    def test_thieu_phuong_o_quan_co_phuong(self):
        kq = convert_old_address(HCM, "Quận 3", "")
        self.assertEqual(kq["ket_qua"], "khong_thay")
        self.assertTrue(kq["ly_do"])


class TestLookupAddress(unittest.TestCase):
    def test_khong_dau_kem_p(self):
        kq = lookup_address("hcm", "p. ban co")
        self.assertTrue(kq["ok"])
        self.assertEqual(kq["khop"], "phường Bàn Cờ")
        self.assertEqual(kq["tinh"], HCM)

    def test_khong_ton_tai(self):
        kq = lookup_address(HCM, "phường không tồn tại")
        self.assertFalse(kq["ok"])
        self.assertIsNone(kq["khop"])
        self.assertTrue(kq["ly_do"])
        self.assertLessEqual(len(kq["goi_y"]), 3)

    def test_goi_y_gan_giong(self):
        kq = lookup_address(HCM, "phường Bàn Cơ Mới")
        self.assertFalse(kq["ok"])
        self.assertIn("phường Bàn Cờ", kq["goi_y"])
        self.assertLessEqual(len(kq["goi_y"]), 3)

    def test_ten_bat_dau_bang_chu_p(self):
        kq = lookup_address(HCM, "Phú Nhuận")
        self.assertTrue(kq["ok"])
        self.assertEqual(kq["khop"], "phường Phú Nhuận")

    def test_tinh_cu(self):
        kq = lookup_address("Bình Dương", "phường Dĩ An")
        self.assertTrue(kq["ok"])
        self.assertEqual(kq["khop"], "phường Dĩ An")
        self.assertEqual(kq["tinh"], HCM)

    def test_tinh_cu_khong_chua_phuong(self):
        # phường Bàn Cờ hình thành từ phường của Quận 3 (TP HCM cũ), không thuộc Bình Dương cũ
        kq = lookup_address("Bình Dương", "phường Bàn Cờ")
        self.assertFalse(kq["ok"])
        self.assertIsNone(kq["khop"])
        self.assertNotIn("phường Bàn Cờ", kq["goi_y"])
        self.assertTrue(kq["ly_do"])
        # ghi TP Hồ Chí Minh (mới) thì vẫn tra toàn bảng
        self.assertEqual(lookup_address(HCM, "phường Dĩ An")["khop"], "phường Dĩ An")
        self.assertEqual(lookup_address("brvt", "phường Vũng Tàu")["khop"], "phường Vũng Tàu")

    def test_trung_ten_khi_bo_dau(self):
        # xã Thanh An (khoản 145) và xã Thạnh An (khoản 164) giống nhau khi bỏ dấu
        self.assertEqual(lookup_address(HCM, "xã Thạnh An")["khop"], "xã Thạnh An")
        self.assertEqual(lookup_address(HCM, "xã Thanh An")["khop"], "xã Thanh An")
        kq = lookup_address(HCM, "xa thanh an")
        self.assertFalse(kq["ok"])
        self.assertEqual(set(kq["goi_y"]), {"xã Thanh An", "xã Thạnh An"})

    def test_chu_so_khong_phai_ascii_khong_lam_dung(self):
        for phuong in ["Phường ²", "²", "p.²"]:
            with self.subTest(phuong=phuong):
                kq = lookup_address("hcm", phuong)
                self.assertFalse(kq["ok"])
                self.assertIsNone(kq["khop"])
                self.assertTrue(kq["ly_do"])

    def test_ngoai_pham_vi(self):
        kq = lookup_address("Hà Nội", "phường Hoàn Kiếm")
        self.assertFalse(kq["ok"])
        self.assertTrue(kq["ly_do"])


class TestCreateDraftOrder(unittest.TestCase):
    INFO = {"ten_nguoi_nhan": "Mai", "sdt": "0912345678", "dia_chi_chi_tiet": "12 Lê Lợi",
            "phuong_xa": "phường Bàn Cờ", "tinh_thanh": HCM, "san_pham": "áo thun", "so_luong": 2,
            "ma_hoi_thoai": "HT-1", "can_cu": "đường Lê Lợi", "do_chac": "cao"}

    def test_on_dinh(self):
        a, b = create_draft_order(dict(self.INFO)), create_draft_order(dict(self.INFO))
        self.assertEqual(a["ma_don"], b["ma_don"])
        self.assertTrue(a["ma_don"].startswith("DN-"))
        self.assertTrue(a["ma_van_don"].startswith("GHN-NHAP-"))
        self.assertEqual(a["ma_don"][3:], a["ma_van_don"][9:])
        self.assertEqual(a["trang_thai"], "cho_duyet")

    def test_khac_truong_khoa_thi_khac_ma(self):
        goc = create_draft_order(dict(self.INFO))["ma_don"]
        for k, v in [("so_luong", 3), ("dia_chi_chi_tiet", "14 Lê Lợi"), ("ma_hoi_thoai", "HT-2")]:
            with self.subTest(truong=k):
                self.assertNotEqual(create_draft_order(dict(self.INFO, **{k: v}))["ma_don"], goc)

    def test_truong_model_tu_viet_khong_doi_ma(self):
        goc = create_draft_order(dict(self.INFO))["ma_don"]
        for k, v in [("can_cu", "khách nói gần chợ"), ("do_chac", "thap"), ("phuong_xa_moi_de_xuat", "x")]:
            with self.subTest(truong=k):
                self.assertEqual(create_draft_order(dict(self.INFO, **{k: v}))["ma_don"], goc)


if __name__ == "__main__":
    unittest.main()
