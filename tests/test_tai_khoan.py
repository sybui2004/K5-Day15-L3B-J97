"""Test codebase/tai_khoan.py: mật khẩu, đăng ký, đăng nhập, phiên, giới hạn tần suất.
Chạy: python -m unittest discover -s tests -v
"""
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "codebase"))

import kho  # noqa: E402
import tai_khoan as tk  # noqa: E402


class TestMatKhau(unittest.TestCase):
    def test_bam_va_kiem(self):
        b = tk.bam_mat_khau("bimat123")
        self.assertTrue(b.startswith("scrypt$"))
        self.assertTrue(tk.kiem_mat_khau("bimat123", b))
        self.assertFalse(tk.kiem_mat_khau("bimat124", b))
        self.assertNotEqual(b, tk.bam_mat_khau("bimat123"))  # muối khác nhau
        self.assertFalse(tk.kiem_mat_khau("x", "hỏng"))


class TestGioiHan(unittest.TestCase):
    def test_gioi_han_cua_so_truot(self):
        g = tk.GioiHan(2, 10)
        g.dung("a", bay_gio=0)
        g.dung("a", bay_gio=1)
        with self.assertRaises(tk.QuaGioiHan) as e:
            g.dung("a", bay_gio=2)
        self.assertEqual(e.exception.cho_giay, 8)
        g.dung("b", bay_gio=2)  # khoá khác
        g.dung("a", bay_gio=11)  # lần đầu đã ra khỏi cửa sổ


class TestQuanLyTaiKhoan(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ql = tk.QuanLyTaiKhoan(kho.KhoFile(os.path.join(self.tmp.name, "nk.jsonl")), mat_khau_admin="admin")

    def tearDown(self):
        self.tmp.cleanup()

    def test_dang_ky_hop_le_va_chuan_hoa(self):
        t = self.ql.dang_ky("  Lan.Nguyen ", "matkhau1", "matkhau1", "1.1.1.1")
        self.assertEqual((t["username"], t["vai"]), ("lan.nguyen", "khach"))
        self.assertIsInstance(t["id"], int)
        self.assertEqual(self.ql.dang_nhap("LAN.NGUYEN", "matkhau1", "1.1.1.1")["id"], t["id"])

    def test_dang_ky_sai(self):
        for u, mk, nl in (("ab", "matkhau1", "matkhau1"), ("admin", "matkhau1", "matkhau1"),
                          ("lan!", "matkhau1", "matkhau1"), ("x" * 33, "matkhau1", "matkhau1"),
                          ("lan", "12345", "12345"), ("lan", "matkhau1", "matkhau2"), ("lan", "a" * 129, "a" * 129)):
            with self.assertRaises(tk.LoiDangNhap, msg=(u, mk, nl)):
                self.ql.dang_ky(u, mk, nl, "1.1.1.%d" % len(u))

    def test_trung_ten(self):
        self.ql.dang_ky("lan", "matkhau1", "matkhau1", "1.1.1.1")
        with self.assertRaises(tk.LoiDangNhap):
            self.ql.dang_ky("lan", "matkhau2", "matkhau2", "2.2.2.2")

    def test_gioi_han_dang_ky_theo_ip(self):
        for i in range(5):
            self.ql.dang_ky("khach%d" % i, "matkhau1", "matkhau1", "9.9.9.9")
        with self.assertRaises(tk.QuaGioiHan) as e:
            self.ql.dang_ky("khach5", "matkhau1", "matkhau1", "9.9.9.9")
        self.assertGreater(e.exception.cho_giay, 0)
        self.ql.dang_ky("khach6", "matkhau1", "matkhau1", "8.8.8.8")

    def test_dang_nhap_sai_bi_chan(self):
        self.ql.dang_ky("mai", "matkhau1", "matkhau1", "1.1.1.1")
        for _ in range(10):
            with self.assertRaises(tk.LoiDangNhap):
                self.ql.dang_nhap("mai", "sai-roi", "3.3.3.3")
        with self.assertRaises(tk.QuaGioiHan):
            self.ql.dang_nhap("mai", "matkhau1", "3.3.3.3")
        self.assertEqual(self.ql.dang_nhap("mai", "matkhau1", "4.4.4.4")["username"], "mai")

    def test_admin(self):
        a = self.ql.dang_nhap("admin", "admin", "1.1.1.1")
        self.assertEqual(a, {"id": 0, "username": "admin", "vai": "shop"})
        with self.assertRaises(tk.LoiDangNhap):
            self.ql.dang_nhap("admin", "sai", "1.1.1.1")

    def test_phien(self):
        t = self.ql.dang_ky("hoa", "matkhau1", "matkhau1", "1.1.1.1")
        token = self.ql.tao_phien(t)
        self.assertEqual(self.ql.doc_phien(token), t)
        a = self.ql.tao_phien(self.ql.dang_nhap("admin", "admin", "1.1.1.1"))
        self.assertEqual(self.ql.doc_phien(a)["vai"], "shop")
        self.assertIsNone(self.ql.doc_phien("khong-co"))
        self.assertIsNone(self.ql.doc_phien(None))
        self.ql.xoa_phien(token)
        self.assertIsNone(self.ql.doc_phien(token))

    def test_phien_het_han(self):
        t = self.ql.dang_ky("binh", "matkhau1", "matkhau1", "1.1.1.1")
        token = self.ql.tao_phien(t)
        self.ql.kho.luu_phien(tk.bam_token(token), t["id"], time.time() - 1)
        self.assertIsNone(self.ql.doc_phien(token))


if __name__ == "__main__":
    unittest.main()
