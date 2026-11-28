"""Test nơi lưu nhật ký (codebase/kho.py): file .jsonl, và Postgres khi có TEST_DATABASE_URL.

Chạy Postgres: TEST_DATABASE_URL=postgresql://user:pass@host:5432/db python -m unittest tests.test_kho -v
Test Postgres dùng schema riêng rồi xoá, không đụng bảng thật.
"""
import os
import sys
import tempfile
import unittest
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "codebase"))

import kho  # noqa: E402

DUYET = {"ma_hoi_thoai": "HT-1", "quyet_dinh_ai": "TAO_DON_NHAP", "truong_da_sua": ["sdt"], "so_luot_hoi_lai": 1,
         "ket_qua": "da_duyet", "luc": "2026-11-27T10:00:00"}
LAN = {"ma_hoi_thoai": "HT-M01", "nguon": "moi", "quyet_dinh": "HOI_LAI", "luc": "2026-11-27T10:00:01",
       "trace": {"tokens_in": 10, "tokens_out": 5, "buoc": [{"loai": "tool", "ten": "validate_phone"}]}}


class _ChungKho:
    def test_ghi_roi_doc_moi_nhat_truoc(self):
        self.k.ghi_duyet(DUYET)
        self.k.ghi_duyet(dict(DUYET, ma_hoi_thoai="HT-2", ket_qua="da_huy", truong_da_sua=[]))
        self.k.ghi_lan_chay(LAN)
        nk = self.k.doc_nhat_ky()
        self.assertEqual([d["ma_hoi_thoai"] for d in nk["duyet"]], ["HT-2", "HT-1"])
        self.assertEqual(nk["duyet"][1]["truong_da_sua"], ["sdt"])
        self.assertEqual(nk["duyet"][1]["luc"], "2026-11-27T10:00:00")
        [lan] = nk["lan_chay"]
        self.assertEqual(lan["trace"]["buoc"][0]["ten"], "validate_phone")
        self.assertEqual(lan["nguon"], "moi")

    # ---- chat khách (spec 2026-11-28-chat-khach-hitl §5.7) ----
    def test_tai_khoan_trung_ten(self):
        i = self.k.tao_tai_khoan("lan", "scrypt$a$b", "khach", "1.2.3.4")
        self.assertIsInstance(i, int)
        with self.assertRaises(kho.TrungTen):
            self.k.tao_tai_khoan("lan", "scrypt$c$d", "khach", "1.2.3.4")
        tk = self.k.tim_tai_khoan("lan")
        self.assertEqual((tk["id"], tk["username"], tk["mat_khau_bam"], tk["vai"]), (i, "lan", "scrypt$a$b", "khach"))
        self.assertIsNone(self.k.tim_tai_khoan("khong-co"))

    def test_phien(self):
        i = self.k.tao_tai_khoan("mai", "x", "khach", "1.1.1.1")
        self.k.luu_phien("bam1", i, 2_000_000_000.0)
        p = self.k.doc_phien("bam1")
        self.assertEqual((p["tai_khoan_id"], p["username"], p["vai"]), (i, "mai", "khach"))
        self.assertAlmostEqual(p["het_han"], 2_000_000_000.0, places=0)
        self.k.xoa_phien("bam1")
        self.assertIsNone(self.k.doc_phien("bam1"))

    def test_tin_theo_thu_tu_va_sau_id(self):
        i = self.k.tao_tai_khoan("hoa", "x", "khach", "1.1.1.1")
        j = self.k.tao_tai_khoan("binh", "x", "khach", "1.1.1.1")
        t1 = self.k.ghi_tin(i, "khach", "lấy 1 áo")
        self.k.ghi_tin(j, "khach", "của người khác")
        t2 = self.k.ghi_tin(i, "bot", "dạ cho em xin sđt")
        t3 = self.k.ghi_tin(i, "khach", "0900000001")
        self.assertLess(t1["id"], t2["id"])
        self.assertEqual([t["noi_dung"] for t in self.k.doc_tin(i)], ["lấy 1 áo", "dạ cho em xin sđt", "0900000001"])
        self.assertEqual([t["id"] for t in self.k.doc_tin(i, sau_id=t1["id"])], [t2["id"], t3["id"]])
        self.assertEqual(t2["nguoi_noi"], "bot")

    def test_cuoc_chat_va_don_cu_ben_sau_khi_mo_lai(self):
        i = self.k.tao_tai_khoan("an", "x", "khach", "1.1.1.1")
        d = {"che_do": "shop", "trang_thai": "cho_duyet", "phien_ban": 3, "kq": {"quyet_dinh": "TAO_DON_NHAP"},
             "ma_don": "DN-1", "ma_van_don": "GHN-NHAP-1", "co_tin_chua_doc": True, "moc_tin_id": 7}
        self.k.luu_cuoc_chat(i, d)
        self.k.luu_cuoc_chat(i, dict(d, phien_ban=4))  # ghi đè
        self.k.ghi_don_cu(i, {"moc_tin_id": 5, "ket_qua": "da_duyet", "ma_don": "DN-0", "truong": {"sdt": "0900000001"},
                              "luc": "2026-11-28T10:00:00"})
        k2 = self.mo_lai()
        [c] = k2.doc_cac_cuoc_chat()
        self.assertEqual((c["tai_khoan_id"], c["username"], c["phien_ban"], c["che_do"], c["kq"]),
                         (i, "an", 4, "shop", {"quyet_dinh": "TAO_DON_NHAP"}))
        self.assertTrue(c["co_tin_chua_doc"])
        [dc] = k2.doc_don_cu(i)
        self.assertEqual((dc["ma_don"], dc["ket_qua"], dc["truong"]), ("DN-0", "da_duyet", {"sdt": "0900000001"}))
        self.assertEqual(k2.tim_tai_khoan("an")["id"], i)

    def test_gioi_han(self):
        for i in range(5):
            self.k.ghi_duyet(dict(DUYET, ma_hoi_thoai="HT-%d" % i))
        self.assertEqual([d["ma_hoi_thoai"] for d in self.k.doc_nhat_ky(2)["duyet"]], ["HT-4", "HT-3"])


class TestKhoFile(_ChungKho, unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.k = kho.KhoFile(os.path.join(self.tmp.name, "nk.jsonl"))

    def mo_lai(self):
        return kho.KhoFile(os.path.join(self.tmp.name, "nk.jsonl"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_chua_co_file_thi_rong(self):
        self.assertEqual(self.k.doc_nhat_ky(), {"duyet": [], "lan_chay": []})

    def test_dong_hong_bi_bo_qua(self):
        self.k.ghi_duyet(DUYET)
        with open(self.k.nhat_ky, "a", encoding="utf-8") as f:
            f.write("{hỏng\n")
        self.assertEqual(len(self.k.doc_nhat_ky()["duyet"]), 1)


class TestMoKho(unittest.TestCase):
    def test_khong_co_database_url_thi_dung_file(self):
        goc = os.environ.pop("DATABASE_URL", None)
        try:
            self.assertEqual(kho.mo_kho().ten, "file")
        finally:
            if goc is not None:
                os.environ["DATABASE_URL"] = goc

    def test_postgres_khong_toi_duoc_thi_bao_loi_kho(self):
        if not CO_PSYCOPG:
            self.skipTest("chưa cài psycopg")
        with self.assertRaises(kho.LoiKho):
            kho.KhoPostgres("postgresql://x:y@127.0.0.1:1/khong_co")


try:
    import psycopg  # noqa: F401
    CO_PSYCOPG = True
except ImportError:
    CO_PSYCOPG = False


@unittest.skipUnless(os.environ.get("TEST_DATABASE_URL") and CO_PSYCOPG,
                     "đặt TEST_DATABASE_URL và cài psycopg để chạy test Postgres")
class TestKhoPostgres(_ChungKho, unittest.TestCase):
    def setUp(self):
        import psycopg
        self.schema = "test_" + uuid.uuid4().hex[:8]
        url = os.environ["TEST_DATABASE_URL"]
        with psycopg.connect(url, autocommit=True) as c:
            c.execute("CREATE SCHEMA %s" % self.schema)
        sep = "&" if "?" in url else "?"
        self.url = url + sep + "options=-csearch_path%3D" + self.schema
        self.k = kho.KhoPostgres(self.url)

    def mo_lai(self):
        return kho.KhoPostgres(self.url)

    def tearDown(self):
        import psycopg
        with psycopg.connect(os.environ["TEST_DATABASE_URL"], autocommit=True) as c:
            c.execute("DROP SCHEMA %s CASCADE" % self.schema)


if __name__ == "__main__":
    unittest.main()
