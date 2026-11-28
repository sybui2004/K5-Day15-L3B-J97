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


class TestGioiHanPost(unittest.TestCase):
    """/api/moi phải nhận được hội thoại hợp lệ lớn nhất (30 lượt × 2.000 ký tự tiếng Việt / emoji)."""

    def setUp(self):
        import threading

        class ManHinhGia:
            def tao_moi(self, luot, ma_khach=None):
                return {"ma_hoi_thoai": "HT-M01", "do_dai": len(web.kiem_hoi_thoai_moi(luot, ma_khach))}

            def huy(self, ma):
                return {"ma_hoi_thoai": ma}

        self.cong_goc = web.PORT
        self.server = web.MayChu(("127.0.0.1", 0), web.XuLyYeuCau)
        web.PORT = self.server.server_address[1]
        web.XuLyYeuCau.man_hinh = ManHinhGia()
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        web.PORT, web.XuLyYeuCau.man_hinh = self.cong_goc, None

    def gui(self, duong, body):
        import http.client
        c = http.client.HTTPConnection("127.0.0.1", web.PORT, timeout=10)
        c.request("POST", duong, body=body, headers={"Host": "127.0.0.1:%d" % web.PORT, "X-Man-Hinh-Duyet": "1",
                                                     "Content-Type": "application/json"})
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
