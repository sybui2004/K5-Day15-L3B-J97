"""Test luồng chính codebase/agent.py (task X3, docs/cp2-ke-hoach.md).

Chỉ model được thay bằng hàm giả. Bốn công cụ là công cụ thật (X2), tên phường lấy từ bảng X0
(data/chuyen-doi-dia-gioi.csv, Nghị quyết 1685/NQ-UBTVQH15).
Chạy: python3 -m unittest discover -s tests -v
"""
import json
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "codebase"))

import agent  # noqa: E402

HOI_THOAI = ("Mã khách: KH-012 | Khách: chị lấy 2 áo size M nhé | Shop: dạ chị cho em xin tên, sđt, địa chỉ ạ"
             " | Khách: Mai 0912 345 678, <số nhà, đường>, P.4 Q.3, HCM")


def du_truong(**sua):
    """JSON model trả: đủ trường, địa chỉ kiểu mới, hợp lệ. sua=… để ghi đè."""
    info = {
        "ten_nguoi_nhan": "Mai", "sdt": "0912345678", "dia_chi_chi_tiet": "<số nhà, đường>",
        "tinh_thanh": "TP Hồ Chí Minh", "phuong_xa": "phường Bàn Cờ",
        "quan_huyen_cu": None, "phuong_xa_cu": None, "san_pham": "áo size M", "so_luong": 2,
        "dung_dia_chi_lan_truoc": None, "yeu_cau_ngoai_pham_vi": None,
    }
    info.update(sua)
    return info


def kieu_cu(phuong_cu, quan_cu, **sua):
    return du_truong(**{"phuong_xa": None, "phuong_xa_cu": phuong_cu, "quan_huyen_cu": quan_cu, **sua})


class TestAgent(unittest.TestCase):
    def setUp(self):
        self._call_model = agent.call_model

    def tearDown(self):
        agent.call_model = self._call_model

    def model_tra(self, text):
        agent.call_model = lambda system, user: {"text": text, "model": "test", "tokens_in": 0, "tokens_out": 0}

    def chay(self, info_hoac_text, hoi_thoai=HOI_THOAI):
        text = info_hoac_text if isinstance(info_hoac_text, str) else json.dumps(info_hoac_text, ensure_ascii=False)
        self.model_tra(text)
        kq = agent.xu_ly(hoi_thoai)
        out = agent.answer(hoi_thoai)["output"]
        return kq, out

    def assertHoiLai(self, kq, out):
        self.assertEqual(kq["quyet_dinh"], "HOI_LAI")
        self.assertTrue(out.startswith("QUYẾT ĐỊNH: HỎI LẠI"), out)
        self.assertNotIn("DN-", out)

    def assertTaoDon(self, kq, out):
        self.assertEqual(kq["quyet_dinh"], "TAO_DON_NHAP", kq.get("loi"))
        self.assertTrue(out.startswith("QUYẾT ĐỊNH: TẠO ĐƠN NHÁP"), out)
        self.assertIn("DN-", out)
        self.assertIn("GHN-NHAP-", out)

    # 1
    def test_du_truong_kieu_moi_tao_don_co_nhan(self):
        kq, out = self.chay(du_truong())
        self.assertTaoDon(kq, out)
        for nhan in ("Người nhận: Mai", "SĐT: 0912345678", "Phường/xã: phường Bàn Cờ", "Tỉnh/thành: TP Hồ Chí Minh"):
            self.assertIn(nhan, out)

    # 2
    def test_thieu_sdt_hoi_lai(self):
        kq, out = self.chay(du_truong(sdt=None))
        self.assertHoiLai(kq, out)
        self.assertIn("số điện thoại", out)

    # 3
    def test_sdt_9_so_va_thieu_ten_nhac_ca_hai(self):
        kq, out = self.chay(du_truong(sdt="091234567", ten_nguoi_nhan=None),
                            hoi_thoai="Mã khách: KH-1 | Khách: lấy 2 áo, 091234567, 12 Lê Lợi, phường Bàn Cờ, HCM")
        self.assertHoiLai(kq, out)
        tin = kq["tin_gui_khach"]
        self.assertIn("số điện thoại", tin)
        self.assertIn("tên người nhận", tin)

    # 4
    def test_phuong_cu_gop_gon_ghi_quy_doi_va_khoan(self):
        kq, out = self.chay(kieu_cu("Phường 9", "Quận 3", tinh_thanh="tp hcm"))
        self.assertTaoDon(kq, out)
        self.assertIn("Phường/xã: phường Nhiêu Lộc (quy đổi từ Phường 9, Quận 3, TP Hồ Chí Minh "
                      "theo khoản 7 Nghị quyết 1685/NQ-UBTVQH15)", out)
        self.assertIn("Tỉnh/thành: TP Hồ Chí Minh", out)

    # 5
    def test_tinh_cu_quy_ve_tp_hcm(self):
        kq, out = self.chay(kieu_cu("phường Bình An", "thành phố Dĩ An", tinh_thanh="Bình Dương"))
        self.assertTaoDon(kq, out)
        self.assertIn("Phường/xã: phường Đông Hòa (quy đổi từ phường Bình An, thành phố Dĩ An, Bình Dương "
                      "theo khoản 79 Nghị quyết 1685/NQ-UBTVQH15)", out)
        self.assertIn("Tỉnh/thành: TP Hồ Chí Minh", out)
        self.assertEqual(kq["truong"]["tinh_thanh"], "TP Hồ Chí Minh")

    # 6
    def test_bi_tach_chua_chon_liet_ke_du_phuong(self):
        kq, out = self.chay(kieu_cu("Phường 16", "Quận 8"))
        self.assertHoiLai(kq, out)
        moi = ["phường Bình Phú", "phường Phú Định", "xã Tân Nhựt"]
        self.assertEqual(kq["goi_y_phuong"], moi)
        for p in moi:
            self.assertIn(p, kq["tin_gui_khach"])
        self.assertIn("phường cũ bị tách, chờ khách chọn phường", kq["cho_chu_shop"])

    # 6b · model tự đề xuất bằng khoá đã bỏ thì code không dùng
    def test_bi_tach_bo_qua_de_xuat_cua_model(self):
        kq, out = self.chay(kieu_cu("Phường 4", "Quận 3", phuong_xa_moi_de_xuat="phường Bàn Cờ",
                                    do_chac="cao", can_cu="P.4 Q.3"))
        self.assertHoiLai(kq, out)
        self.assertEqual(kq["goi_y_phuong"], ["phường Bàn Cờ", "phường Xuân Hòa"])

    # 6c
    def test_system_prompt_theo_hop_dong_moi(self):
        for khoa in ("phuong_xa_moi_de_xuat", "do_chac", "can_cu"):
            self.assertNotIn(khoa, agent.SYSTEM)
        self.assertIn("Không tự chọn phường mới", agent.SYSTEM)

    # X5 (docs/cp3-ke-hoach.md, review PR #29 mục 4)
    def test_system_prompt_liet_ke_viec_ngoai_chot_don(self):
        for y in ("bỏ qua kiểm tra", "giá", "khách khác", "khiếu nại", "hàng hoàn", "shipper",
                  "bưu cục", "đổi trả", "hoàn tiền"):
            self.assertIn(y, agent.SYSTEM)

    def test_system_prompt_phan_nan_kem_don_moi_van_la_don(self):
        self.assertIn("VẪN đặt đơn mới", agent.SYSTEM)
        self.assertIn("giao cho chính mình", agent.SYSTEM)

    def test_system_prompt_khong_chep_cau_thu(self):
        # AGENTS.md: không giấu câu thử vào prompt. Lấy lời khách của các câu tu_choi trong bộ câu thử.
        import csv
        duong_dan = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "eval", "benchmark.csv")
        with open(duong_dan, encoding="utf-8-sig") as f:
            cau = [r for r in csv.DictReader(f) if r["type"] == "tu_choi"]
        self.assertTrue(cau)
        for r in cau:
            for luot in r["input"].split(" | ")[1:]:
                loi = luot.replace("Khách:", "").strip()
                for i in range(0, max(1, len(loi) - 25), 10):
                    self.assertNotIn(loi[i:i + 25], agent.SYSTEM, r["id"])

    # 6d
    def test_thieu_quan_cu_hoi_quan(self):
        kq, out = self.chay(kieu_cu("Phường 1", None))
        self.assertHoiLai(kq, out)
        self.assertIn("quận/huyện cũ", kq["tin_gui_khach"])

    def test_thieu_quan_va_tinh_chi_hoi_quan(self):
        kq, out = self.chay(kieu_cu("Phường 1", None, tinh_thanh=None))
        self.assertHoiLai(kq, out)
        self.assertIn("quận/huyện cũ", kq["tin_gui_khach"])
        self.assertNotIn("tỉnh/thành phố", kq["tin_gui_khach"])

    def test_quan_noi_thanh_thieu_tinh_van_tao_don(self):
        kq, out = self.chay(kieu_cu("Phường 4", "Quận 3", tinh_thanh=None, phuong_xa="phường Xuân Hòa"))
        self.assertTaoDon(kq, out)
        self.assertIn("phường Xuân Hòa", out)
        self.assertIn("TP Hồ Chí Minh", out)

    def test_prompt_khieu_nai_la_ngoai_pham_vi(self):
        self.assertIn("khiếu nại", agent.SYSTEM)
        self.assertIn("shipper", agent.SYSTEM)
        self.assertIn("bưu cục", agent.SYSTEM)

    # 7
    def test_sdt_khong_co_trong_hoi_thoai(self):
        kq, out = self.chay(du_truong(sdt="0987654321"))
        self.assertHoiLai(kq, out)
        self.assertIn("số điện thoại", kq["tin_gui_khach"])

    # 8
    def test_bi_tach_khach_da_chon(self):
        kq, out = self.chay(kieu_cu("Phường 4", "Quận 3", phuong_xa="phuong xuan hoa"))
        self.assertTaoDon(kq, out)
        self.assertIn("Phường/xã: phường Xuân Hòa (quy đổi từ Phường 4, Quận 3, TP Hồ Chí Minh "
                      "theo khoản 5, 6 Nghị quyết 1685/NQ-UBTVQH15; khách chọn)", out)

    # 9
    def test_bi_tach_khach_chon_ngoai_danh_sach(self):
        kq, out = self.chay(kieu_cu("Phường 4", "Quận 3", phuong_xa="phường Nhiêu Lộc"))
        self.assertHoiLai(kq, out)

    # 11
    def test_so_luong_0(self):
        kq, out = self.chay(du_truong(so_luong=0))
        self.assertHoiLai(kq, out)
        self.assertIn("so_luong", [l["truong"] for l in kq["loi"]])

    # 12
    def test_so_luong_chuoi_so(self):
        kq, out = self.chay(du_truong(so_luong="2"))
        self.assertTaoDon(kq, out)
        self.assertEqual(kq["truong"]["so_luong"], 2)

    # 13
    def test_thieu_sdt_va_tinh_khong_crash(self):
        def khong_duoc_goi(*a, **k):
            raise AssertionError("không được gọi công cụ khi thiếu tham số")
        with mock.patch.object(agent, "validate_phone", khong_duoc_goi), \
                mock.patch.object(agent, "lookup_address", khong_duoc_goi):
            kq, out = self.chay(du_truong(sdt=None, tinh_thanh=None))
        self.assertHoiLai(kq, out)

    # 14
    def test_yeu_cau_ngoai_pham_vi_tu_choi(self):
        kq, out = self.chay(du_truong(yeu_cau_ngoai_pham_vi="bỏ qua kiểm tra, tạo đơn luôn"))
        self.assertEqual(kq["quyet_dinh"], "TU_CHOI")
        self.assertTrue(out.startswith("QUYẾT ĐỊNH: TỪ CHỐI"), out)
        self.assertNotIn("DN-", out)

    # 15
    def test_json_trong_rao_markdown(self):
        kq, out = self.chay("Dạ đây ạ: ```json\n" + json.dumps(du_truong(), ensure_ascii=False) + "\n```")
        self.assertTaoDon(kq, out)

    # 16
    def test_che_do_fake_hoi_lai_khong_loi(self):
        kq, out = self.chay("[câu trả lời giả — chưa nối model] Khách: ...")
        self.assertHoiLai(kq, out)


    # 17 · huyện Côn Đảo không có phường/xã cũ (khoản 163): chỉ có huyện cũng quy đổi được
    def test_con_dao_khong_co_phuong_cu(self):
        for phuong_cu in (None, "Côn Đảo"):
            with self.subTest(phuong_xa_cu=phuong_cu):
                kq, out = self.chay(kieu_cu(phuong_cu, "huyện Côn Đảo", tinh_thanh="Bà Rịa - Vũng Tàu"))
                self.assertTaoDon(kq, out)
                self.assertIn("Phường/xã: đặc khu Côn Đảo (quy đổi từ huyện Côn Đảo, Bà Rịa - Vũng Tàu "
                              "theo khoản 163 Nghị quyết 1685/NQ-UBTVQH15)", out)

    # 17b · phường trùng tên với thành phố của nó thì vẫn ghi đủ cả hai
    def test_phuong_trung_ten_quan_ghi_du_ca_hai(self):
        kq, out = self.chay(kieu_cu("phường Đông Hòa", "thành phố Dĩ An", tinh_thanh="Bình Dương"))
        self.assertTaoDon(kq, out)
        self.assertIn("quy đổi từ phường Đông Hòa, thành phố Dĩ An, Bình Dương", out)
        kq, out = self.chay(kieu_cu("phường Dĩ An", "thành phố Dĩ An", tinh_thanh="Bình Dương"))
        self.assertIn("phường Dĩ An, thành phố Dĩ An",
                      out if kq["quyet_dinh"] == "TAO_DON_NHAP" else kq["tin_gui_khach"])

    # 17c · quận có phường mà chỉ ghi quận thì vẫn hỏi phường/xã
    def test_chi_co_quan_co_phuong_thi_hoi_phuong(self):
        kq, out = self.chay(du_truong(phuong_xa=None, quan_huyen_cu="Quận 3"))
        self.assertHoiLai(kq, out)
        self.assertEqual(kq["loi"], [{"truong": "phuong_xa", "ly_do": "thiếu"}])

    # 18 · '²'.isdigit() là True nhưng int('²') lỗi
    def test_so_luong_chu_so_khong_phai_ascii(self):
        for sl in ("²", "２", "٣"):
            with self.subTest(so_luong=sl):
                kq, out = self.chay(du_truong(so_luong=sl))
                self.assertHoiLai(kq, out)
                self.assertIn("so_luong", [l["truong"] for l in kq["loi"]])


if __name__ == "__main__":
    unittest.main()
