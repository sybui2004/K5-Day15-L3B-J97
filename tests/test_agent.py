"""Test luồng chính codebase/agent.py (task X3, docs/cp2-ke-hoach.md).

Model và bốn công cụ đều được thay bằng hàm giả, nên test không phụ thuộc bảng X0 hay model thật.
Tên phường ở đây là tên giả ("Phường Mới A"…), chỉ để kiểm logic quyết định ở 1.3 (d).
Chạy: python3 -m unittest discover -s tests -v
"""
import hashlib
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "codebase"))

import agent  # noqa: E402

HOI_THOAI = ("Mã khách: KH-012 | Khách: chị lấy 2 áo size M nhé | Shop: dạ chị cho em xin tên, sđt, địa chỉ ạ"
             " | Khách: Mai 0912 345 678, 12 Lê Lợi, P.7 Q.3, HCM, gần chợ Bến Thành")

# ---- bảng giả cho công cụ giả ----
BANG_CU = {  # (phường cũ, quận cũ) đã chuẩn hoá → phường mới
    ("1", "9"): ["Phường Mới C"],                    # Phường 1, Quận 9: gộp gọn
    ("7", "3"): ["Phường Mới A", "Phường Mới B"],     # Phường 7, Quận 3: bị tách
}
PHUONG_MOI = {"Phường Mới A", "Phường Mới B", "Phường Mới C", "Phường Bến Thành"}


def _key(s):
    return agent.chuan_hoa_ten(s)


def fake_validate_phone(sdt):
    s = "".join(ch for ch in str(sdt) if ch.isdigit() or ch == "+")
    if s.startswith("+84"):
        s = "0" + s[3:]
    elif s.startswith("84"):
        s = "0" + s[2:]
    ok = len(s) == 10 and s[:2] in ("03", "05", "07", "08", "09")
    return {"ok": ok, "sdt_chuan": s if ok else None, "ly_do": "" if ok else "sđt phải đủ 10 số"}


def fake_convert_old_address(tinh_thanh, quan_huyen_cu, phuong_xa_cu):
    moi = BANG_CU.get((_key(phuong_xa_cu), _key(quan_huyen_cu)))
    if not moi:
        return {"ket_qua": "khong_thay", "phuong_moi": []}
    return {"ket_qua": "mot" if len(moi) == 1 else "nhieu", "phuong_moi": list(moi)}


def fake_lookup_address(tinh_thanh, phuong_xa):
    for p in PHUONG_MOI:
        if _key(p) == _key(phuong_xa):
            return {"ok": True, "khop": p, "goi_y": [], "ly_do": ""}
    return {"ok": False, "khop": None, "goi_y": sorted(PHUONG_MOI)[:3], "ly_do": "không có phường này"}


def fake_create_draft_order(info):
    raw = json.dumps(info, sort_keys=True, ensure_ascii=False, default=str)
    h = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8]
    return {"ma_don": "DN-" + h, "ma_van_don": "GHN-NHAP-" + h, "trang_thai": "cho_duyet"}


def du_truong(**sua):
    """JSON model trả: đủ trường, địa chỉ kiểu mới, hợp lệ. sua=… để ghi đè."""
    info = {
        "ten_nguoi_nhan": "Mai", "sdt": "0912345678", "dia_chi_chi_tiet": "12 Lê Lợi",
        "tinh_thanh": "TP Hồ Chí Minh", "phuong_xa": "Phường Bến Thành",
        "quan_huyen_cu": None, "phuong_xa_cu": None, "phuong_xa_moi_de_xuat": None,
        "do_chac": None, "can_cu": None, "san_pham": "áo size M", "so_luong": 2,
        "dung_dia_chi_lan_truoc": None, "yeu_cau_ngoai_pham_vi": None,
    }
    info.update(sua)
    return info


def kieu_cu(phuong_cu, quan_cu, **sua):
    return du_truong(**{"phuong_xa": None, "phuong_xa_cu": phuong_cu, "quan_huyen_cu": quan_cu, **sua})


class TestAgent(unittest.TestCase):
    def setUp(self):
        self._goc = {k: getattr(agent, k) for k in
                     ("call_model", "validate_phone", "convert_old_address", "lookup_address", "create_draft_order")}
        agent.validate_phone = fake_validate_phone
        agent.convert_old_address = fake_convert_old_address
        agent.lookup_address = fake_lookup_address
        agent.create_draft_order = fake_create_draft_order

    def tearDown(self):
        for k, v in self._goc.items():
            setattr(agent, k, v)

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
        for nhan in ("Người nhận: Mai", "SĐT: 0912345678", "Phường/xã: Phường Bến Thành", "Tỉnh/thành: TP Hồ Chí Minh"):
            self.assertIn(nhan, out)

    # 2
    def test_thieu_sdt_hoi_lai(self):
        kq, out = self.chay(du_truong(sdt=None))
        self.assertHoiLai(kq, out)
        self.assertIn("số điện thoại", out)

    # 3
    def test_sdt_9_so_va_thieu_ten_nhac_ca_hai(self):
        kq, out = self.chay(du_truong(sdt="091234567", ten_nguoi_nhan=None),
                            hoi_thoai="Mã khách: KH-1 | Khách: lấy 2 áo, 091234567, 12 Lê Lợi, P. Bến Thành, HCM")
        self.assertHoiLai(kq, out)
        tin = kq["tin_gui_khach"]
        self.assertIn("số điện thoại", tin)
        self.assertIn("tên người nhận", tin)

    # 4
    def test_phuong_cu_gop_gon_tao_don_co_quy_doi(self):
        kq, out = self.chay(kieu_cu("Phường 1", "Quận 9"))
        self.assertTaoDon(kq, out)
        self.assertIn("quy đổi từ", out)
        self.assertIn("Phường Mới C", out)

    # 5
    def test_bi_tach_de_xuat_co_can_cu_trong_hoi_thoai(self):
        kq, out = self.chay(kieu_cu("Phường 7", "Quận 3", phuong_xa_moi_de_xuat="Phường Mới A",
                                    do_chac="cao", can_cu="gần chợ Bến Thành"))
        self.assertTaoDon(kq, out)
        self.assertIn("AI chọn theo", out)
        self.assertIn("Phường Mới A", out)

    # 6
    def test_bi_tach_can_cu_khong_co_trong_hoi_thoai(self):
        kq, out = self.chay(kieu_cu("Phường 7", "Quận 3", phuong_xa_moi_de_xuat="Phường Mới A",
                                    do_chac="cao", can_cu="gần nhà thờ Đức Bà"))
        self.assertHoiLai(kq, out)

    # 7
    def test_sdt_khong_co_trong_hoi_thoai(self):
        kq, out = self.chay(du_truong(sdt="0987654321"))
        self.assertHoiLai(kq, out)
        self.assertIn("số điện thoại", kq["tin_gui_khach"])

    # 8
    def test_bi_tach_do_chac_thap_liet_ke_phuong(self):
        kq, out = self.chay(kieu_cu("Phường 7", "Quận 3", phuong_xa_moi_de_xuat="Phường Mới A", do_chac="thap"))
        self.assertHoiLai(kq, out)
        self.assertIn("Phường Mới A", kq["tin_gui_khach"])
        self.assertIn("Phường Mới B", kq["tin_gui_khach"])
        self.assertEqual(kq["goi_y_phuong"], ["Phường Mới A", "Phường Mới B"])

    # 9
    def test_bi_tach_de_xuat_ngoai_danh_sach(self):
        kq, out = self.chay(kieu_cu("Phường 7", "Quận 3", phuong_xa_moi_de_xuat="Phường Mới C",
                                    do_chac="cao", can_cu="gần chợ Bến Thành"))
        self.assertHoiLai(kq, out)

    # 10
    def test_bi_tach_khach_da_chon(self):
        kq, out = self.chay(kieu_cu("Phường 7", "Quận 3", phuong_xa="phuong moi b", do_chac="thap"))
        self.assertTaoDon(kq, out)
        self.assertIn("Phường/xã: Phường Mới B", out)

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
        agent.validate_phone = khong_duoc_goi
        agent.lookup_address = khong_duoc_goi
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


if __name__ == "__main__":
    unittest.main()
