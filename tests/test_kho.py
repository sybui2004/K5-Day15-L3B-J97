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

    def test_gioi_han(self):
        for i in range(5):
            self.k.ghi_duyet(dict(DUYET, ma_hoi_thoai="HT-%d" % i))
        self.assertEqual([d["ma_hoi_thoai"] for d in self.k.doc_nhat_ky(2)["duyet"]], ["HT-4", "HT-3"])


class TestKhoFile(_ChungKho, unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.k = kho.KhoFile(os.path.join(self.tmp.name, "nk.jsonl"))

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

    def tearDown(self):
        import psycopg
        with psycopg.connect(os.environ["TEST_DATABASE_URL"], autocommit=True) as c:
            c.execute("DROP SCHEMA %s CASCADE" % self.schema)


if __name__ == "__main__":
    unittest.main()
