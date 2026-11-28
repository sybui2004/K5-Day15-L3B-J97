"""Test màn hình duyệt (codebase/web.py, task P2): hàm kiểm khi sửa, ghép câu trả lời (luồng B), duyệt/huỷ, nhật ký.

Không test giao diện. Chỉ model được thay bằng hàm giả; agent, hộp thư và công cụ là code thật.
Chạy: python -m unittest discover -s tests -v
"""
import json
import os
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "codebase"))
# Test luồng cũ không gọi lớp chặn NeMo (máy có .env thật sẽ gọi API). Guard có test riêng: tests/test_guard.py,
# TestGuardTrongAgent.
os.environ["GUARD"] = "tat"

import agent  # noqa: E402
import tracing  # noqa: E402
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
        hop_thu = [
            {"ma_hoi_thoai": "HT-1", "ma_khach": "KH-1", "text": "Mã khách: KH-1 | Khách: Mai 0900000001 bàn cờ"},
            {"ma_hoi_thoai": "HT-2", "ma_khach": "KH-2", "text": "Mã khách: KH-2 | Khách: Lan 0900000005 P.4 Q.3"},
            {"ma_hoi_thoai": "HT-3", "ma_khach": None, "text": "", "loi_doc": "hop-thu.jsonl, dòng 3: hỏng"},
        ]
        self.mh_text_goc = {h["ma_hoi_thoai"]: h["text"] for h in hop_thu}
        self.mh.tai(hop_thu)

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

    def test_ghi_nhat_ky_loi_thi_khong_chot_va_thu_lai_duoc(self):
        goc = self.mh.kho.ghi_duyet

        def hong(dong):
            raise OSError("đĩa đầy")
        self.mh.kho.ghi_duyet = hong
        try:
            for thao_tac, ma in ((lambda: self.mh.duyet("HT-1", {}), "HT-1"), (lambda: self.mh.huy("HT-2"), "HT-2")):
                truoc = self.mh.lay(ma)
                with self.assertRaisesRegex(web.LoiThaoTac, "nhật ký"):
                    thao_tac()
                self.assertEqual(self.mh.lay(ma), truoc)
        finally:
            self.mh.kho.ghi_duyet = goc
        self.assertEqual(self.mh.duyet("HT-1", {})["trang_thai"], "da_duyet")
        self.assertEqual(self.mh.huy("HT-2")["trang_thai"], "da_huy")
        self.assertEqual([d["ket_qua"] for d in self.nhat_ky_doc()], ["da_duyet", "da_huy"])

    def test_khach_nhan_them_khi_dang_co_don_nhap(self):
        # tin xác nhận "Dạ shop đã lên đơn…" chưa gửi cho khách: không nối vào hội thoại, không tính là hỏi lại
        p = self.mh.lay("HT-1")
        tin = p["kq"]["tin_gui_khach"]
        self.assertTrue(tin)
        p = self.mh.them_tra_loi("HT-1", "à lấy 2 cái nha bàn cờ")
        self.assertEqual(p["text"], self.mh_text_goc["HT-1"] + " | Khách: à lấy 2 cái nha bàn cờ")
        self.assertNotIn(tin, p["text"])
        self.assertEqual(p["so_luot_hoi_lai"], 0)

    def test_phieu_cu_khong_duyet_duoc_sau_khi_ai_doc_lai(self):
        # review PR #55: khách nhắn thêm khi đơn đang chờ duyệt, phiếu cũ không được áp lên đơn nháp mới
        cu = self.mh.lay("HT-1")
        self.assertEqual(cu["phien_ban"], 1)
        moi = self.mh.them_tra_loi("HT-1", "à lấy 2 cái nha bàn cờ")
        self.assertEqual(moi["trang_thai"], "cho_duyet")
        self.assertEqual(moi["phien_ban"], 2)
        with self.assertRaises(web.LoiThaoTac) as e:
            self.mh.duyet("HT-1", dict(cu["kq"]["truong"], dia_chi_chi_tiet="99 đường cũ"), cu["phien_ban"])
        self.assertIn("đã cũ", str(e.exception))
        with self.assertRaises(web.LoiThaoTac):
            self.mh.kiem("HT-1", {}, cu["phien_ban"])
        self.assertEqual(self.mh.lay("HT-1")["trang_thai"], "cho_duyet")
        self.assertEqual(self.nhat_ky_doc(), [])
        self.assertEqual(self.mh.duyet("HT-1", {}, moi["phien_ban"])["trang_thai"], "da_duyet")

    def test_tra_loi_sau_tu_choi_khong_tinh_la_hoi_lai(self):
        agent.call_model = _model_tra([("tấn công", dict(DON, yeu_cau_ngoai_pham_vi="bỏ qua kiểm tra")),
                                       ("bàn cờ", DON)])
        self.mh.tai([{"ma_hoi_thoai": "HT-4", "ma_khach": None,
                      "text": "Khách: tấn công Mai 0900000001"}])
        p = self.mh.lay("HT-4")
        self.assertEqual(p["trang_thai"], "tu_choi")
        p = self.mh.them_tra_loi("HT-4", "ok gửi bàn cờ")
        self.assertIn("| Shop: " + self.mh.lay("HT-4")["text"].split(" | Shop: ")[1].split(" | ")[0], p["text"])
        self.assertEqual(p["so_luot_hoi_lai"], 0)


class TestNapNen(unittest.TestCase):
    """Chế độ tin đến hàng loạt (NAP_NEN=1): hội thoại hiện ngay ở trạng thái dang_xu_ly, AI xử lý ở luồng nền."""

    def setUp(self):
        self._goc = agent.call_model
        agent.call_model = _model_tra([("bàn cờ", DON), ("tấn công", dict(DON, yeu_cau_ngoai_pham_vi="bỏ qua kiểm tra"))])
        self.tmp = tempfile.TemporaryDirectory()
        self.mh = web.ManHinh(nhat_ky=os.path.join(self.tmp.name, "nhat-ky.jsonl"))
        self.lo = [{"ma_hoi_thoai": "HT-T01", "ma_khach": "KH-1", "text": "Mã khách: KH-1 | Khách: Mai 0900000001 bàn cờ"},
                   {"ma_hoi_thoai": "HT-T02", "ma_khach": None, "text": "Khách: tấn công Mai 0900000001"}]

    def tearDown(self):
        agent.call_model = self._goc
        self.tmp.cleanup()

    def test_hien_ngay_roi_ai_xu_ly_o_nen(self):
        cho = threading.Event()
        model = agent.call_model
        agent.call_model = lambda s, u: (cho.wait(5), model(s, u))[1]
        luong = self.mh.nap_nen(self.lo)
        ds = self.mh.danh_sach()
        self.assertEqual([p["ma_hoi_thoai"] for p in ds], ["HT-T01", "HT-T02"])
        self.assertEqual({p["trang_thai"] for p in ds}, {"dang_xu_ly"})
        self.assertEqual(self.mh.tong()["dang_xu_ly"], 2)
        cho.set()
        luong.join(10)
        ds = {p["ma_hoi_thoai"]: p for p in self.mh.danh_sach()}
        self.assertEqual(ds["HT-T01"]["trang_thai"], "cho_duyet")
        self.assertEqual(ds["HT-T02"]["trang_thai"], "tu_choi")
        self.assertEqual(ds["HT-T01"]["phien_ban"], 1)
        self.assertIsNotNone(ds["HT-T01"]["trace"])
        t = self.mh.tong()
        self.assertEqual((t["dang_xu_ly"], t["lan_chay"]), (0, 2))

    def test_anh_chup_danh_sach_va_tong_khop_nhau(self):
        # review PR #59: worker xong hội thoại cuối giữa lúc đọc danh sách và lúc đọc tổng → trang kẹt "đang xử lý"
        cho = threading.Event()
        model = agent.call_model
        agent.call_model = lambda s, u: (cho.wait(5), model(s, u))[1]
        luong = self.mh.nap_nen(self.lo[:1])
        goc = self.mh._tong_khi_giu_khoa

        def xong_giua_chung(*a):  # chạy trong khi anh_chup đang giữ khoá: worker chưa thể ghi
            cho.set()
            return goc(*a)
        self.mh._tong_khi_giu_khoa = xong_giua_chung
        ds, t = self.mh.anh_chup()
        self.assertEqual(t["dang_xu_ly"], sum(p["trang_thai"] == "dang_xu_ly" for p in ds))
        self.assertEqual(t["dang_xu_ly"], 1)
        luong.join(10)
        ds, t = self.mh.anh_chup()
        self.assertEqual((t["dang_xu_ly"], ds[0]["trang_thai"]), (0, "cho_duyet"))

    def test_lo_moi_len_dau_va_ma_trung_duoc_cap_rieng(self):
        self.mh.nap_nen(self.lo).join(10)
        self.mh.nap_nen(self.lo[:1]).join(10)
        ma = [p["ma_hoi_thoai"] for p in self.mh.danh_sach()]
        self.assertEqual(ma[0], "HT-T01*")
        self.assertEqual(sorted(ma), sorted(["HT-T01", "HT-T02", "HT-T01*"]))

    def test_dang_xu_ly_thi_chua_thao_tac_duoc(self):
        cho = threading.Event()
        model = agent.call_model
        agent.call_model = lambda s, u: (cho.wait(5), model(s, u))[1]
        luong = self.mh.nap_nen(self.lo[:1])
        for thao_tac in (lambda: self.mh.huy("HT-T01"), lambda: self.mh.them_tra_loi("HT-T01", "x"),
                         lambda: self.mh.duyet("HT-T01", {})):
            with self.assertRaises(web.LoiThaoTac):
                thao_tac()
        cho.set()
        luong.join(10)
        self.assertEqual(self.mh.lay("HT-T01")["trang_thai"], "cho_duyet")

    def test_ai_loi_thi_chuyen_cho_khach_va_ghi_trace(self):
        def hong(system, user):
            raise RuntimeError("mất mạng")
        agent.call_model = hong
        self.mh.nap_nen(self.lo[:1]).join(10)
        p = self.mh.lay("HT-T01")
        self.assertEqual(p["trang_thai"], "cho_khach")
        self.assertIn("mất mạng", json.dumps(p["kq"], ensure_ascii=False))  # xu_ly_hop_thu tự bắt lỗi từng hội thoại
        self.assertEqual(self.mh.tong()["lan_chay"], 1)


class TestTaoMoiVaTrace(unittest.TestCase):
    """Hội thoại tạo trên màn hình (demo câu thử lạ), trace + chi phí từng lần chạy, nhật ký."""

    def setUp(self):
        self._goc = agent.call_model
        agent.call_model = tracing.model_call(_model_tra([("bàn cờ", DON), ("Bàn Cờ", DON)]))  # đếm như model thật
        self.tmp = tempfile.TemporaryDirectory()
        self.mh = web.ManHinh(nhat_ky=os.path.join(self.tmp.name, "nhat-ky.jsonl"))
        self.mh.tai([{"ma_hoi_thoai": "HT-1", "ma_khach": "KH-1", "text": "Mã khách: KH-1 | Khách: Mai bàn cờ"}])

    def tearDown(self):
        agent.call_model = self._goc
        self.tmp.cleanup()

    LUOT = [{"vai": "khach", "tin": "lấy 1 áo size M"}, {"vai": "shop", "tin": "dạ chị cho em xin địa chỉ"},
            {"vai": "khach", "tin": "Mai 0900000001, 12 hẻm 5, phường Bàn Cờ, HCM"}]

    def test_tao_moi_chay_ai_va_len_dau_hop_thu(self):
        p = self.mh.tao_moi(self.LUOT, "KH-9")
        self.assertEqual(p["ma_hoi_thoai"], "HT-M01")
        self.assertEqual(p["nguon"], "moi")
        self.assertEqual(p["trang_thai"], "cho_duyet")
        self.assertTrue(p["text"].startswith("Mã khách: KH-9 | Khách: lấy 1 áo size M | Shop: "))
        self.assertEqual(self.mh.danh_sach()[0]["ma_hoi_thoai"], "HT-M01")
        self.assertEqual(self.mh.tao_moi(self.LUOT)["ma_hoi_thoai"], "HT-M02")
        self.assertEqual(self.mh.duyet("HT-M01", {})["trang_thai"], "da_duyet")

    def test_tao_moi_sai_dau_vao(self):
        sai = [([], None), ([{"vai": "shop", "tin": "chào"}], None), ([{"vai": "bot", "tin": "x"}], None),
               ([{"vai": "khach", "tin": "  "}], None), ([{"vai": "khach", "tin": "x" * 2001}], None),
               (self.LUOT, "khách 9"), ("không phải danh sách", None), ([{"vai": "khach"}], None),
               ([{"vai": "khach", "tin": "x"}] * 31, None)]
        for luot, ma_khach in sai:
            with self.subTest(luot=str(luot)[:40], ma_khach=ma_khach):
                with self.assertRaises(web.LoiThaoTac):
                    self.mh.tao_moi(luot, ma_khach)
        self.assertEqual(len(self.mh.danh_sach()), 1)
        self.assertEqual(self.mh.tao_moi(self.LUOT)["ma_hoi_thoai"], "HT-M01")

    def test_model_loi_khi_tao_moi_thi_khong_them(self):
        def hong(system, user):
            raise ConnectionError("mất mạng")
        agent.call_model = hong
        with self.assertRaisesRegex(web.LoiThaoTac, "mất mạng"):
            self.mh.tao_moi(self.LUOT)
        self.assertEqual(len(self.mh.danh_sach()), 1)

    def test_moi_lan_chay_co_trace_va_cong_vao_tong(self):
        p = self.mh.tao_moi(self.LUOT)
        t = p["trace"]
        self.assertEqual(t["nguon"], "moi")
        self.assertEqual(t["model_calls"], 1)
        loai = [b["loai"] for b in t["buoc"]]
        self.assertIn("model", loai)
        self.assertIn("tool", loai)
        self.assertIn("validate_phone", [b["ten"] for b in t["buoc"]])
        for k in ("tokens_in", "tokens_out", "thoi_gian_s", "chi_phi_usd"):
            self.assertIn(k, t)
        self.assertIsNone(t["chi_phi_usd"])  # model "test" không có giá
        self.assertEqual(self.mh.danh_sach()[1]["trace"]["nguon"], "hop_thu")
        tong = self.mh.tong()
        self.assertEqual(tong["lan_chay"], 2)
        self.assertEqual(tong["model_calls"], 2)
        nk = self.mh.nhat_ky()
        self.assertEqual([d["ma_hoi_thoai"] for d in nk["lan_chay"]], ["HT-M01", "HT-1"])

    def test_tra_loi_cung_ghi_trace(self):
        self.mh.tai([{"ma_hoi_thoai": "HT-2", "ma_khach": None, "text": "Khách: Lan 0900000005"}])
        p = self.mh.them_tra_loi("HT-2", "bàn cờ")
        self.assertEqual(p["trace"]["nguon"], "tra_loi")

    def test_ghi_lan_chay_loi_khong_chan_demo(self):
        def hong(dong):
            raise OSError("Postgres: mất kết nối")
        self.mh.kho.ghi_lan_chay = hong
        self.assertEqual(self.mh.tao_moi(self.LUOT)["trang_thai"], "cho_duyet")
        self.assertEqual(self.mh.tong()["loi_kho"], "Postgres: mất kết nối")

    def test_model_loi_van_ghi_lan_chay_va_cong_tong(self):
        def hong(system, user):
            raise ConnectionError("mất mạng")
        agent.call_model = tracing.model_call(hong)
        with self.assertRaisesRegex(web.LoiThaoTac, "mất mạng"):
            self.mh.tao_moi(self.LUOT)
        tong = self.mh.tong()
        self.assertEqual(tong["lan_chay"], 2)  # HT-1 lúc tải + lần lỗi
        self.assertEqual(tong["model_calls"], 2)
        lan = self.mh.nhat_ky()["lan_chay"][0]
        self.assertEqual(lan["ma_hoi_thoai"], "HT-M01")
        self.assertIsNone(lan["quyet_dinh"])
        self.assertTrue(any("mất mạng" in l for l in lan["trace"]["loi"]))
        self.assertEqual(len(self.mh.danh_sach()), 1)  # không thêm hội thoại
        agent.call_model = tracing.model_call(_model_tra([("bàn cờ", DON)]))
        self.assertEqual(self.mh.tao_moi(self.LUOT)["ma_hoi_thoai"], "HT-M01")  # thử lại được, mã chưa bị chiếm

    def test_model_loi_khi_tra_loi_van_ghi_lan_chay(self):
        def hong(system, user):
            raise ConnectionError("mất mạng")
        truoc = self.mh.lay("HT-1")
        agent.call_model = tracing.model_call(hong)
        with self.assertRaises(web.LoiThaoTac):
            self.mh.them_tra_loi("HT-1", "à lấy 2 cái")
        lan = self.mh.nhat_ky()["lan_chay"][0]
        self.assertEqual((lan["ma_hoi_thoai"], lan["nguon"], lan["quyet_dinh"]), ("HT-1", "tra_loi", None))
        self.assertEqual(self.mh.tong()["lan_chay"], 2)
        sau = self.mh.lay("HT-1")
        self.assertEqual((sau["text"], sau["trang_thai"], sau["trace"]), (truoc["text"], truoc["trang_thai"], truoc["trace"]))

    def test_nhat_ky_khoi_dong_theo_thu_tu_chay(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        mh = web.ManHinh(nhat_ky=os.path.join(tmp.name, "nhat-ky.jsonl"))
        mh.tai([{"ma_hoi_thoai": "HT-A", "ma_khach": None, "text": "Khách: Lan 0900000005"},  # thiếu → HỎI LẠI
                {"ma_hoi_thoai": "HT-B", "ma_khach": "KH-1", "text": "Khách: Mai 0900000001, 12 hẻm 5, phường Bàn Cờ, HCM, lấy 1 áo size M"}])
        self.assertEqual([p["ma_hoi_thoai"] for p in mh.danh_sach()], ["HT-B", "HT-A"])  # đơn nháp lên đầu
        self.assertEqual([d["ma_hoi_thoai"] for d in mh.nhat_ky()["lan_chay"]], ["HT-B", "HT-A"])  # mới nhất trước
        self.assertEqual([d["quyet_dinh"] for d in mh.nhat_ky()["lan_chay"]], ["TAO_DON_NHAP", "HOI_LAI"])

    def test_ma_trung_dung_cung_ma_o_hop_thu_va_nhat_ky(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        mh = web.ManHinh(nhat_ky=os.path.join(tmp.name, "nhat-ky.jsonl"))
        mh.tai([{"ma_hoi_thoai": "HT-1", "ma_khach": None, "text": "Khách: Lan 0900000005"},  # HỎI LẠI
                {"ma_hoi_thoai": "HT-1", "ma_khach": None,
                 "text": "Khách: Mai 0900000001, 12 hẻm 5, phường Bàn Cờ, HCM, lấy 1 áo size M"}])  # ĐƠN NHÁP
        hop_thu = {p["ma_hoi_thoai"]: p["kq"]["quyet_dinh"] for p in mh.danh_sach()}
        self.assertEqual(hop_thu, {"HT-1": "HOI_LAI", "HT-1*": "TAO_DON_NHAP"})
        nhat_ky = {d["ma_hoi_thoai"]: d["quyet_dinh"] for d in mh.nhat_ky()["lan_chay"]}
        self.assertEqual(nhat_ky, hop_thu)


class TestChiPhi(unittest.TestCase):
    GIA = [{"model": "claude-sonnet-5-5", "input": 3, "output": 15}, {"model": "x", "input": None, "output": 1}]

    def test_tinh_theo_trieu_token(self):
        self.assertAlmostEqual(web.chi_phi("claude-sonnet-5-5", 1_000_000, 100_000, self.GIA), 4.5)

    def test_ten_model_co_hau_to_ngay(self):
        self.assertAlmostEqual(web.chi_phi("claude-sonnet-5-5-20261101", 1000, 0, self.GIA), 0.003)

    def test_khong_co_gia(self):
        self.assertIsNone(web.chi_phi("test", 10, 10, self.GIA))
        self.assertIsNone(web.chi_phi("x", 10, 10, self.GIA))
        self.assertIsNone(web.chi_phi("", 10, 10, self.GIA))

    def test_hai_model_trong_mot_lan_chay_tinh_rieng(self):
        # review PR #55: lớp chặn và bước đọc đơn (hoặc model dự phòng) dùng hai model khác giá
        gia = self.GIA + [{"model": "claude-haiku-5-5", "input": 1, "output": 5}]
        su_kien = [{"kind": "model", "model": "claude-haiku-5-5", "tokens_in": 1_000_000, "tokens_out": 0},
                   {"kind": "tool", "name": "validate_phone"},
                   {"kind": "model", "model": "claude-sonnet-5-5", "tokens_in": 1_000_000, "tokens_out": 0}]
        self.assertAlmostEqual(web.chi_phi_su_kien(su_kien, gia), 1 + 3)

    def test_mot_lan_goi_chua_co_gia_thi_ca_lan_chay_chua_du_gia(self):
        su_kien = [{"kind": "model", "model": "claude-sonnet-5-5", "tokens_in": 1000, "tokens_out": 0},
                   {"kind": "model", "model": "model-la", "tokens_in": 1000, "tokens_out": 0}]
        self.assertIsNone(web.chi_phi_su_kien(su_kien, self.GIA))
        self.assertIsNone(web.chi_phi_su_kien([{"kind": "tool"}], self.GIA))


class TestTepTinh(unittest.TestCase):
    """Giao diện ở codebase/static/: chỉ phục vụ file trong thư mục đó, đúng loại nội dung."""

    def test_trang_chinh_va_tai_nguyen(self):
        for duong, loai in (("/", "text/html"), ("/app.js", "text/javascript"), ("/app.css", "text/css"),
                            ("/fonts/fonts.css", "text/css"), ("/fonts/manrope-vietnamese.woff2", "font/woff2")):
            with self.subTest(duong=duong):
                tep = web.tep_tinh(duong)
                self.assertIsNotNone(tep)
                self.assertTrue(tep[1].startswith(loai))
                self.assertTrue(tep[0])

    def test_khong_ra_ngoai_thu_muc_static(self):
        for duong in ("/../web.py", "/fonts/../../kho.py", "/%2e%2e/web.py", "/..\\web.py", "/khong-co.js",
                      "/fonts/", "//etc/passwd", "/.env"):
            with self.subTest(duong=duong):
                self.assertIsNone(web.tep_tinh(duong))

    def test_query_string_bi_bo_qua(self):
        self.assertEqual(web.tep_tinh("/app.js?v=2")[1], web.tep_tinh("/app.js")[1])


class TestKhoiChay(unittest.TestCase):
    def test_cong_ban_thi_khong_goi_model(self):
        import socket
        s = socket.socket()
        s.bind(("127.0.0.1", 0))  # giữ một cổng trống làm "cổng bận"
        s.listen(1)
        cong_goc, tai_goc, doc_goc = web.PORT, web.ManHinh.tai, web.doc_hop_thu
        da_tai = []
        web.PORT = s.getsockname()[1]
        web.ManHinh.tai = lambda self, h: da_tai.append(h)
        web.doc_hop_thu = lambda: [{"ma_hoi_thoai": "HT-1", "ma_khach": None, "text": "Khách: x"}]
        try:
            self.assertEqual(web.main(), 1)
        finally:
            web.PORT, web.ManHinh.tai, web.doc_hop_thu = cong_goc, tai_goc, doc_goc
            s.close()
        self.assertEqual(da_tai, [])


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


class TestChatKhach(unittest.TestCase):
    """Cuộc chat của tài khoản khách (spec chat khách HITL §5.4)."""

    def setUp(self):
        import tai_khoan
        self._goc = agent.call_model
        self.goi_model = []
        self.cho_model = threading.Event()
        self.cho_model.set()
        self.model_bat_dau = threading.Event()
        tra = _model_tra([("đủ-tin Mai 0900000001", DON), ("thiếu-sdt", dict(DON, sdt=None))])

        def model(system, user):
            self.goi_model.append(user)
            self.model_bat_dau.set()
            self.cho_model.wait(5)
            return tra(system, user)
        agent.call_model = model
        self.tmp = tempfile.TemporaryDirectory()
        self.kho = __import__("kho").KhoFile(os.path.join(self.tmp.name, "nk.jsonl"))
        self.mh = web.ManHinh(kho=self.kho)
        self.ql = tai_khoan.QuanLyTaiKhoan(self.kho, "admin")
        self.lan = self.ql.dang_ky("lan", "matkhau1", "matkhau1", "1.1.1.1")
        self.mai = self.ql.dang_ky("mai", "matkhau1", "matkhau1", "1.1.1.2")

    def tearDown(self):
        self.cho_model.set()
        self.mh.cho_chat_xong(5)
        agent.call_model = self._goc
        self.tmp.cleanup()

    def gui(self, tk, tin, cho=True):
        t = self.mh.khach_gui(tk, tin)
        if cho:
            self.assertTrue(self.mh.cho_chat_xong(5))
        return t

    def tin(self, tk, nguoi=None):
        ds = self.mh.khach_doc(tk, 0)["tin"]
        return [t for t in ds if nguoi is None or t["nguoi_noi"] == nguoi]

    def test_bot_tra_loi_hoi_lai(self):
        self.gui(self.lan, "lấy 1 áo thiếu-sdt")
        [bot] = self.tin(self.lan, "bot")
        self.assertTrue(bot["noi_dung"])
        self.assertEqual(self.mh.lay("TK-lan")["trang_thai"], "cho_khach")

    def test_tao_don_nhap_khong_hua_len_don(self):
        self.gui(self.lan, "lấy 1 áo đủ-tin Mai 0900000001")
        [bot] = self.tin(self.lan, "bot")
        self.assertIn("Dạ shop đã ghi nhận đơn của anh/chị: Mai · 0900000001 · 12 hẻm 5, phường Bàn Cờ, TP Hồ Chí Minh",
                      bot["noi_dung"])
        self.assertIn("Shop kiểm lại rồi xác nhận ngay ạ.", bot["noi_dung"])
        self.assertNotIn("đã lên đơn", bot["noi_dung"])
        p = self.mh.lay("TK-lan")
        self.assertEqual((p["trang_thai"], p["nguon"], p["che_do"]), ("cho_duyet", "khach", "bot"))

    def test_khach_chi_thay_tin_cua_minh(self):
        self.gui(self.lan, "của lan thiếu-sdt")
        self.gui(self.mai, "của mai thiếu-sdt")
        self.assertTrue(all("lan" in t["noi_dung"] for t in self.tin(self.lan, "khach")))
        self.assertEqual([t["noi_dung"] for t in self.tin(self.mai, "khach")], ["của mai thiếu-sdt"])

    def test_gop_tin_trong_hang_doi(self):
        self.cho_model.clear()
        self.gui(self.lan, "tin 1 thiếu-sdt", cho=False)
        self.assertTrue(self.model_bat_dau.wait(5))
        self.assertTrue(self.mh.khach_doc(self.lan, 0)["dang_soan"])
        self.gui(self.lan, "tin 2", cho=False)
        self.gui(self.lan, "tin 3 đủ-tin Mai 0900000001", cho=False)
        self.cho_model.set()
        self.assertTrue(self.mh.cho_chat_xong(5))
        bot = self.tin(self.lan, "bot")
        self.assertEqual(len(bot), 1)  # chỉ trả lời theo văn bản mới nhất
        self.assertIn("đã ghi nhận đơn", bot[0]["noi_dung"])
        self.assertIn("tin 3", self.goi_model[-1])
        self.assertFalse(self.mh.khach_doc(self.lan, 0)["dang_soan"])

    def test_tiep_quan_giua_luc_ai_chay(self):
        self.cho_model.clear()
        self.gui(self.lan, "lấy áo đủ-tin Mai 0900000001", cho=False)
        self.assertTrue(self.model_bat_dau.wait(5))
        self.mh.shop_nhan("TK-lan", "Dạ chị chờ shop chút ạ")
        self.cho_model.set()
        self.assertTrue(self.mh.cho_chat_xong(5))
        nguoi = [t["nguoi_noi"] for t in self.tin(self.lan)]
        self.assertEqual(nguoi, ["khach", "shop"])  # không có tin bot sau tin shop
        p = self.mh.lay("TK-lan")
        self.assertEqual((p["che_do"], p["trang_thai"]), ("shop", "cho_duyet"))  # đơn nháp vẫn cập nhật

    def test_che_do_shop_tin_khach_khong_chay_ai_va_phieu_cu(self):
        self.gui(self.lan, "lấy áo đủ-tin Mai 0900000001")
        self.mh.shop_nhan("TK-lan", "Dạ chị xác nhận giúp shop ạ")
        cu = self.mh.lay("TK-lan")["phien_ban"]
        so_lan = len(self.goi_model)
        self.gui(self.lan, "à đổi sang 2 áo")
        p = self.mh.lay("TK-lan")
        self.assertEqual(len(self.goi_model), so_lan)
        self.assertGreater(p["phien_ban"], cu)
        self.assertTrue(p["co_tin_chua_doc"])
        with self.assertRaises(web.LoiThaoTac):
            self.mh.duyet("TK-lan", {}, cu)
        p = self.mh.shop_doc_lai("TK-lan")
        self.assertFalse(p["co_tin_chua_doc"])
        self.assertEqual(len(self.goi_model), so_lan + 1)
        self.assertEqual(self.tin(self.lan, "bot")[-1]["id"], self.tin(self.lan, "bot")[0]["id"])  # đọc lại không nhắn

    def test_tra_bot_chay_tu_tin_ke_tiep(self):
        self.gui(self.lan, "xin chào thiếu-sdt")
        self.mh.shop_nhan("TK-lan", "Dạ shop chào chị")
        self.gui(self.lan, "cho chị 1 áo thiếu-sdt")
        so_bot = len(self.tin(self.lan, "bot"))
        so_lan = len(self.goi_model)
        self.mh.shop_tra_bot("TK-lan")
        self.assertTrue(self.mh.cho_chat_xong(5))
        self.assertEqual(len(self.goi_model), so_lan)  # trả lại bot không tự chạy
        self.gui(self.lan, "sđt chị đây đủ-tin Mai 0900000001")
        self.assertEqual(len(self.tin(self.lan, "bot")), so_bot + 1)
        self.assertEqual(self.mh.lay("TK-lan")["che_do"], "bot")

    def test_duyet_them_tin_he_thong_va_mo_don_moi(self):
        self.gui(self.lan, "đơn đầu đủ-tin Mai 0900000001")
        p = self.mh.lay("TK-lan")
        da = self.mh.duyet("TK-lan", {}, p["phien_ban"])
        [ht] = self.tin(self.lan, "he_thong")
        self.assertRegex(ht["noi_dung"], r"^Đơn DN-\w+ đã được shop xác nhận\.$")
        self.assertEqual(len(da["don_cu"]), 1)
        self.assertEqual(da["don_cu"][0]["ket_qua"], "da_duyet")
        self.assertEqual(da["trang_thai"], "cho_khach")
        self.gui(self.lan, "đơn thứ hai thiếu-sdt")
        self.assertNotIn("đơn đầu", self.goi_model[-1])  # AI chỉ đọc tin sau mốc
        self.assertIn("đơn thứ hai", self.goi_model[-1])

    def test_huy_mo_don_moi_khong_nhan_khach(self):
        self.gui(self.lan, "đơn đủ-tin Mai 0900000001")
        p = self.mh.huy("TK-lan")
        self.assertEqual(self.tin(self.lan, "he_thong"), [])
        self.assertEqual((p["trang_thai"], p["don_cu"][0]["ket_qua"]), ("cho_khach", "da_huy"))

    def test_gioi_han_tin(self):
        import tai_khoan
        with self.assertRaises(web.LoiThaoTac):
            self.mh.khach_gui(self.lan, "x" * 501)
        with self.assertRaises(web.LoiThaoTac):
            self.mh.khach_gui(self.lan, "   ")
        for i in range(5):
            self.gui(self.mai, "tin %d thiếu-sdt" % i)
        with self.assertRaises(tai_khoan.QuaGioiHan):
            self.mh.khach_gui(self.mai, "tin 6")

    def test_dung_lai_sau_khoi_dong(self):
        self.gui(self.lan, "đơn lan đủ-tin Mai 0900000001")
        self.gui(self.mai, "đơn mai đủ-tin Mai 0900000001")
        self.mh.duyet("TK-mai", {}, self.mh.lay("TK-mai")["phien_ban"])
        self.mh.shop_nhan("TK-mai", "cảm ơn chị")

        def khong_duoc_goi(system, user):
            raise AssertionError("không được gọi model khi dựng lại")
        agent.call_model = khong_duoc_goi
        mh2 = web.ManHinh(kho=self.kho)
        mh2.nap_cuoc_chat()
        lan, mai = mh2.lay("TK-lan"), mh2.lay("TK-mai")
        self.assertEqual((lan["trang_thai"], lan["kq"]["quyet_dinh"]), ("cho_duyet", "TAO_DON_NHAP"))
        self.assertEqual((mai["trang_thai"], mai["che_do"], len(mai["don_cu"])), ("cho_khach", "shop", 1))
        self.assertEqual([t["nguoi_noi"] for t in mai["tin"]], ["khach", "bot", "he_thong", "shop"])
        mh2.duyet("TK-lan", {}, lan["phien_ban"])  # phiếu chờ duyệt vẫn duyệt được

    def test_them_tra_loi_tu_choi_hoi_thoai_khach(self):
        self.gui(self.lan, "lấy áo thiếu-sdt")
        with self.assertRaises(web.LoiThaoTac):
            self.mh.them_tra_loi("TK-lan", "shop tự dán")


class _MayChuThu:
    """Dựng máy chủ thật trên cổng tạm, có QuanLyTaiKhoan trên kho file tạm. Lớp con gán self.man_hinh_gia."""

    def dung_may_chu(self, man_hinh):
        import tai_khoan
        self._tmp_tk = tempfile.TemporaryDirectory()
        self.cong_goc = web.PORT
        self.server = web.MayChu(("127.0.0.1", 0), web.XuLyYeuCau)
        web.PORT = self.server.server_address[1]
        web.XuLyYeuCau.man_hinh = man_hinh
        web.XuLyYeuCau.tai_khoan = tai_khoan.QuanLyTaiKhoan(
            __import__("kho").KhoFile(os.path.join(self._tmp_tk.name, "nk.jsonl")), mat_khau_admin="admin")
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def dung_lai(self):
        self.server.shutdown()
        self.server.server_close()
        web.PORT, web.XuLyYeuCau.man_hinh, web.XuLyYeuCau.tai_khoan = self.cong_goc, None, None
        self._tmp_tk.cleanup()

    def goi(self, phuong_thuc, duong, body=None, cookie=None, them=None):
        """Trả (status, headers dict chữ thường, json hoặc None)."""
        import http.client
        c = http.client.HTTPConnection("127.0.0.1", web.PORT, timeout=10)
        h = {"Host": "127.0.0.1:%d" % web.PORT}
        if phuong_thuc == "POST":
            h.update({"X-Man-Hinh-Duyet": "1", "Content-Type": "application/json"})
        if cookie:
            h["Cookie"] = "j97_phien=" + cookie
        h.update(them or {})
        data = body if isinstance(body, bytes) else (json.dumps(body or {}).encode() if phuong_thuc == "POST" else None)
        c.request(phuong_thuc, duong, body=data, headers=h)
        r = c.getresponse()
        raw = r.read()
        hd = {k.lower(): v for k, v in r.getheaders()}
        c.close()
        try:
            return r.status, hd, json.loads(raw or b"null")
        except ValueError:
            return r.status, hd, None

    @staticmethod
    def cookie_tu(hd):
        import re
        m = re.search(r"j97_phien=([^;]*)", hd.get("set-cookie", ""))
        return m.group(1) if m else None

    def dang_nhap_admin(self):
        st, hd, _ = self.goi("POST", "/api/dang-nhap", {"username": "admin", "mat_khau": "admin"})
        assert st == 200, st
        return self.cookie_tu(hd)


class TestChatHttp(_MayChuThu, unittest.TestCase):
    def setUp(self):
        self._goc = agent.call_model
        agent.call_model = _model_tra([("thiếu-sdt", dict(DON, sdt=None))])
        self.tmp = tempfile.TemporaryDirectory()
        self.mh = web.ManHinh(kho=__import__("kho").KhoFile(os.path.join(self.tmp.name, "nk.jsonl")))
        self.dung_may_chu(self.mh)
        web.XuLyYeuCau.tai_khoan.kho = self.mh.kho  # cùng kho với màn hình

    def tearDown(self):
        self.mh.cho_chat_xong(5)
        agent.call_model = self._goc
        self.dung_lai()
        self.tmp.cleanup()

    def khach(self, u):
        st, hd, _ = self.goi("POST", "/api/dang-ky", {"username": u, "mat_khau": "matkhau1", "nhap_lai": "matkhau1"})
        self.assertEqual(st, 200)
        return self.cookie_tu(hd)

    def test_khach_khong_doc_duoc_chat_nguoi_khac(self):
        a, b = self.khach("khach.a"), self.khach("khach.b")
        self.assertEqual(self.goi("POST", "/api/chat/gui", {"tin": "bí mật của A thiếu-sdt"}, cookie=a)[0], 200)
        self.mh.cho_chat_xong(5)
        st, _, d = self.goi("GET", "/api/chat?sau=0", cookie=b)
        self.assertEqual((st, d["tin"]), (200, []))
        st, _, d = self.goi("GET", "/api/chat?sau=0", cookie=a)
        self.assertEqual([t["nguoi_noi"] for t in d["tin"]], ["khach", "bot"])
        self.assertNotIn("kq", json.dumps(d))  # khách không thấy kq / trace

    def test_khach_goi_shop_nhan_403(self):
        a = self.khach("khach.c")
        self.assertEqual(self.goi("POST", "/api/shop/nhan", {"ma": "TK-khach.c", "tin": "x"}, cookie=a)[0], 403)

    def test_chua_dang_nhap_khong_chat(self):
        self.assertEqual(self.goi("GET", "/api/chat?sau=0")[0], 401)
        self.assertEqual(self.goi("POST", "/api/chat/gui", {"tin": "x"})[0], 401)

    def test_gui_qua_nhanh_429(self):
        a = self.khach("khach.d")
        for i in range(5):
            self.assertEqual(self.goi("POST", "/api/chat/gui", {"tin": "t%d thiếu-sdt" % i}, cookie=a)[0], 200)
        st, _, d = self.goi("POST", "/api/chat/gui", {"tin": "t6"}, cookie=a)
        self.assertEqual(st, 429)
        self.assertGreater(d["cho_giay"], 0)

    def test_shop_nhan_khach_thay(self):
        a = self.khach("khach.e")
        self.goi("POST", "/api/chat/gui", {"tin": "chào thiếu-sdt"}, cookie=a)
        self.mh.cho_chat_xong(5)
        ad = self.dang_nhap_admin()
        st, _, p = self.goi("POST", "/api/shop/nhan", {"ma": "TK-khach.e", "tin": "Dạ shop đây ạ"}, cookie=ad)
        self.assertEqual((st, p["che_do"]), (200, "shop"))
        d = self.goi("GET", "/api/chat?sau=0", cookie=a)[2]
        self.assertEqual(d["tin"][-1]["nguoi_noi"], "shop")
        self.assertEqual(self.goi("POST", "/api/shop/tra-bot", {"ma": "TK-khach.e"}, cookie=ad)[2]["che_do"], "bot")


class TestDangNhapHttp(_MayChuThu, unittest.TestCase):
    def setUp(self):
        class ManHinhGia:
            def anh_chup(self):
                return [], {"dang_xu_ly": 0}

            def duyet(self, ma, sua, pb=None):
                return {"ma_hoi_thoai": ma}

        self._trusted_goc = web.TRUSTED_PROXY
        self.dung_may_chu(ManHinhGia())

    def tearDown(self):
        web.TRUSTED_PROXY = self._trusted_goc
        self.dung_lai()

    def dang_ky(self, u, ip_header=None):
        return self.goi("POST", "/api/dang-ky", {"username": u, "mat_khau": "matkhau1", "nhap_lai": "matkhau1"},
                        them={"X-Real-IP": ip_header} if ip_header else None)

    def test_chua_dang_nhap_api_shop_401(self):
        self.assertEqual(self.goi("GET", "/api/hop-thu")[0], 401)
        self.assertEqual(self.goi("POST", "/api/duyet", {"ma": "HT-1"})[0], 401)
        self.assertEqual(self.goi("GET", "/api/toi")[0], 401)

    def test_bi_chan_thi_khong_chay_tiep_vao_api_shop(self):
        goi = []
        self.server.RequestHandlerClass.man_hinh = type("Ghi", (), {
            "anh_chup": lambda s_: goi.append("hop-thu") or ([], {}),
            "nhat_ky": lambda s_: goi.append("nhat-ky") or {},
            "duyet": lambda s_, *a: goi.append("duyet") or {}})()
        ck = self.cookie_tu(self.dang_ky("khach9")[1])
        self.goi("GET", "/api/hop-thu")
        self.goi("GET", "/api/nhat-ky", cookie=ck)
        self.goi("POST", "/api/duyet", {"ma": "HT-1"}, cookie=ck)
        self.goi("POST", "/api/duyet", {"ma": "HT-1"})
        self.assertEqual(goi, [])

    def test_khach_goi_api_shop_403(self):
        st, hd, d = self.dang_ky("khach1")
        self.assertEqual((st, d["vai"]), (200, "khach"))
        ck = self.cookie_tu(hd)
        self.assertEqual(self.goi("GET", "/api/hop-thu", cookie=ck)[0], 403)
        self.assertEqual(self.goi("POST", "/api/duyet", {"ma": "HT-1"}, cookie=ck)[0], 403)
        self.assertEqual(self.goi("GET", "/api/nhat-ky", cookie=ck)[0], 403)

    def test_dang_ky_dat_cookie(self):
        st, hd, _ = self.dang_ky("khach2")
        sc = hd.get("set-cookie", "")
        self.assertEqual(st, 200)
        for phan in ("j97_phien=", "HttpOnly", "SameSite=Strict", "Path=/", "Max-Age=43200"):
            self.assertIn(phan, sc)
        self.assertNotIn("Secure", sc)
        st, _, d = self.goi("GET", "/api/toi", cookie=self.cookie_tu(hd))
        self.assertEqual((st, d), (200, {"vai": "khach", "username": "khach2"}))

    def test_cookie_secure_qua_proxy_tin_cay(self):
        web.TRUSTED_PROXY = web.doc_trusted_proxy("127.0.0.0/8")
        st, hd, _ = self.goi("POST", "/api/dang-nhap", {"username": "admin", "mat_khau": "admin"},
                             them={"X-Forwarded-Proto": "https"})
        self.assertEqual(st, 200)
        self.assertIn("Secure", hd.get("set-cookie", ""))

    def test_khong_tin_header_tu_ngoai(self):
        web.TRUSTED_PROXY = web.doc_trusted_proxy("")
        for i in range(5):
            self.assertEqual(self.dang_ky("ngoai%d" % i, ip_header="10.0.0.%d" % i)[0], 200)
        st, _, d = self.dang_ky("ngoai5", ip_header="10.0.0.99")
        self.assertEqual(st, 429)
        self.assertGreater(d["cho_giay"], 0)
        st, hd, _ = self.goi("POST", "/api/dang-nhap", {"username": "admin", "mat_khau": "admin"},
                             them={"X-Forwarded-Proto": "https"})
        self.assertNotIn("Secure", hd.get("set-cookie", ""))

    def test_tin_header_tu_proxy_tin_cay(self):
        web.TRUSTED_PROXY = web.doc_trusted_proxy("127.0.0.0/8")
        for i in range(6):
            self.assertEqual(self.dang_ky("qua%d" % i, ip_header="10.0.1.%d" % i)[0], 200)

    def test_admin_dang_nhap_vao_hop_thu(self):
        ck = self.dang_nhap_admin()
        self.assertEqual(self.goi("GET", "/api/hop-thu", cookie=ck)[0], 200)
        self.assertEqual(self.goi("GET", "/api/toi", cookie=ck)[2], {"vai": "shop", "username": "admin"})

    def test_dang_nhap_sai_401(self):
        st, _, d = self.goi("POST", "/api/dang-nhap", {"username": "admin", "mat_khau": "sai"})
        self.assertEqual(st, 401)
        self.assertIn("loi", d)

    def test_dang_ky_sai_400(self):
        st, _, d = self.goi("POST", "/api/dang-ky", {"username": "lan", "mat_khau": "matkhau1", "nhap_lai": "khac"})
        self.assertEqual(st, 400)
        self.assertIn("nhập lại", d["loi"])

    def test_dang_xuat(self):
        ck = self.dang_nhap_admin()
        st, hd, _ = self.goi("POST", "/api/dang-xuat", cookie=ck)
        self.assertEqual(st, 200)
        self.assertIn("Max-Age=0", hd.get("set-cookie", ""))
        self.assertEqual(self.goi("GET", "/api/toi", cookie=ck)[0], 401)


class TestGioiHanPost(_MayChuThu, unittest.TestCase):
    """/api/moi phải nhận được hội thoại hợp lệ lớn nhất (30 lượt × 2.000 ký tự tiếng Việt / emoji)."""

    def setUp(self):
        import threading

        class ManHinhGia:
            def tao_moi(self, luot, ma_khach=None):
                return {"ma_hoi_thoai": "HT-M01", "do_dai": len(web.kiem_hoi_thoai_moi(luot, ma_khach))}

            def huy(self, ma):
                return {"ma_hoi_thoai": ma}

        self.dung_may_chu(ManHinhGia())
        self.ck = self.dang_nhap_admin()

    def tearDown(self):
        self.dung_lai()

    def gui(self, duong, body):
        import http.client
        c = http.client.HTTPConnection("127.0.0.1", web.PORT, timeout=10)
        c.request("POST", duong, body=body, headers={"Host": "127.0.0.1:%d" % web.PORT, "X-Man-Hinh-Duyet": "1",
                                                     "Content-Type": "application/json",
                                                     "Cookie": "j97_phien=" + self.ck})
        r = c.getresponse()
        r.read()
        c.close()
        return r.status

    def test_hoi_thoai_hop_le_lon_nhat_qua_duoc(self):
        for tin, ascii_ in (("ế" * 2000, False), ("😀" * 2000, True)):
            body = json.dumps({"luot": [{"vai": "khach", "tin": tin}] * 30}, ensure_ascii=ascii_).encode("utf-8")
            with self.subTest(byte=len(body)):
                self.assertGreater(len(body), 65536)
                self.assertEqual(self.gui("/api/moi", body), 200)

    def test_vuot_gioi_han_thi_413(self):
        self.assertEqual(self.gui("/api/moi", b" " * (web.GIOI_HAN_POST_MOI + 1)), 413)
        self.assertEqual(self.gui("/api/huy", b" " * (web.GIOI_HAN_POST + 1)), 413)  # API khác giữ 64 KB


if __name__ == "__main__":
    unittest.main()


class TestMoKho(unittest.TestCase):
    """Có DATABASE_URL mà Postgres lỗi: chạy máy thì ghi file để demo vẫn chạy; DATABASE_REQUIRED=1 (Docker) thì dừng."""

    def _loi(self, *a, **k):
        raise web.LoiKho("Postgres: password authentication failed")

    def test_mac_dinh_lui_ve_file(self):
        from unittest import mock
        with mock.patch.object(web, "mo_kho", self._loi), mock.patch.dict(os.environ, {"DATABASE_REQUIRED": ""}):
            self.assertIsInstance(web._mo_kho(), web.KhoFile)

    def test_bat_buoc_postgres_thi_dung(self):
        from unittest import mock
        with mock.patch.object(web, "mo_kho", self._loi), mock.patch.dict(os.environ, {"DATABASE_REQUIRED": "1"}):
            with self.assertRaises(SystemExit) as cm:
                web._mo_kho()
            self.assertIn("password authentication failed", str(cm.exception.code))
