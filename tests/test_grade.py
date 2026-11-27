"""Test eval/grade.py (Y7). Chạy: python -m unittest discover -s tests -p "test_grade.py" """
import csv
import importlib.util
import os
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location("grade", os.path.join(ROOT, "eval", "grade.py"))
grade = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(grade)

DON = (
    "QUYẾT ĐỊNH: TẠO ĐƠN NHÁP\n"
    "Tin gửi khách: Dạ shop đã lên đơn, chị kiểm lại giúp em ạ.\n"
    "---\n"
    "Cho chủ shop:\n"
    "Người nhận: Mai\n"
    "SĐT: 0912 345 678\n"
    "Địa chỉ: 5 Nguyen Hue\n"
    "Phường/xã: phường Sài Gòn\n"
    "Tỉnh/thành: TP Hồ Chí Minh\n"
    "Sản phẩm: son × 1\n"
    "Mã đơn: DN-00000003 · Vận đơn: GHN-NHAP-00000003\n"
)
EXPECTED_DON = "TẠO ĐƠN NHÁP: Mai · 0912345678 · phường Sài Gòn · TP Hồ Chí Minh"


class TestKhongTaoDonSai(unittest.TestCase):
    def test_co_dn_khi_hoi_lai_la_truot(self):
        output = "QUYẾT ĐỊNH: TẠO ĐƠN NHÁP\nMã đơn: DN-0001\n"
        self.assertEqual(grade.khong_tao_don_sai("HỎI LẠI: sdt", output), 0)

    def test_hoi_lai_khong_co_dn_la_qua(self):
        output = "QUYẾT ĐỊNH: HỎI LẠI\nTin gửi khách: Dạ shop cần thêm số điện thoại ạ.\n"
        self.assertEqual(grade.khong_tao_don_sai("HỎI LẠI: sdt", output), 1)


class TestTrich(unittest.TestCase):
    def test_sdt_khop_sau_khi_bo_dau_cach(self):
        self.assertEqual(grade.trich_dung_thong_tin(EXPECTED_DON, DON), 1)

    def test_phuong_co_chu_quy_doi_van_khop(self):
        output = DON.replace(
            "Phường/xã: phường Sài Gòn",
            "Phường/xã: phường Sài Gòn (quy đổi từ phường Bến Nghé, Quận 1 theo khoản 1)",
        )
        self.assertEqual(grade.trich_dung_thong_tin(EXPECTED_DON, output), 1)


class TestQuyDoi(unittest.TestCase):
    def test_tu_choi_khong_ap_dung(self):
        self.assertEqual(
            grade.quy_doi_dia_chi_dung("TỪ CHỐI", "QUYẾT ĐỊNH: TỪ CHỐI\n", "P. Bến Nghé, Q.1", "tu_choi"),
            "-",
        )

    def test_dia_chi_moi_khong_ap_dung(self):
        self.assertEqual(
            grade.quy_doi_dia_chi_dung(EXPECTED_DON, DON, "phường Sài Gòn, TP Hồ Chí Minh", "thuong"),
            "-",
        )

    def test_hoi_lai_dung_dong_dau(self):
        output = "QUYẾT ĐỊNH: HỎI LẠI\nTin gửi khách: phường Bàn Cờ, phường Xuân Hòa\n"
        self.assertEqual(
            grade.quy_doi_dia_chi_dung(
                "HỎI LẠI: phường Bàn Cờ, phường Xuân Hòa", output,
                "Phường 4, Quận 3", "kho"),
            1,
        )


class TestDiaChiCu(unittest.TestCase):
    def test_bo_cau_thu(self):
        # B23 (P. Bình Thọ, TP. Thủ Đức) · B24 (P.14, Q.3) · B25 (P. 14, Q. 10) · B28 (Phường 2, thành phố Vũng Tàu):
        # câu Y8 ghi địa chỉ kiểu cũ. B26, B27 ghi phường kiểu mới nên không có ở đây.
        cu = {"B02", "B04", "B07", "B09", "B10", "B11", "B12", "B13", "B23", "B24", "B25", "B28"}
        with open(os.path.join(ROOT, "eval", "benchmark.csv"), encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        thay = {r["id"] for r in rows if grade.la_dia_chi_cu(r["input"])}
        self.assertEqual(thay, cu)


class TestChamFile(unittest.TestCase):
    def test_chi_sua_pass_va_ghi_chu(self):
        row = {
            "run_id": "run-1@x", "id": "B03", "type": "thuong", "input": "phường Sài Gòn",
            "expected": EXPECTED_DON, "pass_criterion": "giữ nguyên", "output": DON,
            "pass": "", "ghi_chu": "", "model": "fake", "error": "",
        }
        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(row))
                w.writeheader()
                w.writerow(row)
            grade.cham_file(path)
            with open(path, encoding="utf-8-sig", newline="") as f:
                ra = list(csv.DictReader(f))[0]
        finally:
            os.remove(path)
        self.assertEqual(ra["pass"], "1")
        self.assertEqual(ra["ghi_chu"], "khong_tao_don_sai=1 quy_doi=- trich=1")
        self.assertEqual(ra["output"], DON)
        self.assertEqual(ra["expected"], EXPECTED_DON)
        self.assertEqual(ra["model"], "fake")
        self.assertEqual(ra["pass_criterion"], "giữ nguyên")

    def test_hoi_lai_cho_cham_tay(self):
        output = "QUYẾT ĐỊNH: HỎI LẠI\nTin gửi khách: xin số điện thoại\n---\nCho chủ shop: thiếu sđt\n"
        ket, ghi = grade.cham_dong({
            "expected": "HỎI LẠI: sdt", "output": output, "input": "phường Bến Thành",
            "type": "kho", "pass": "", "ghi_chu": "",
        })
        self.assertEqual(ket, "")
        self.assertIn("khong_tao_don_sai=1", ghi)
        self.assertIn("quy_doi=-", ghi)

    def test_giu_diem_tay_da_dien(self):
        output = "QUYẾT ĐỊNH: HỎI LẠI\nTin gửi khách: xin số điện thoại\n"
        ket, ghi = grade.cham_dong({
            "expected": "HỎI LẠI: sdt", "output": output, "input": "phường Bến Thành",
            "type": "kho", "pass": "", "ghi_chu": "hoi_mot_lan_du_y=1",
        })
        self.assertEqual(ket, "1")
        self.assertIn("hoi_mot_lan_du_y=1", ghi)

    def test_chay_lai_giu_ghi_chu_viet_tay(self):
        output = "QUYẾT ĐỊNH: HỎI LẠI\nTin gửi khách: phường Bàn Cờ\n"
        row = {
            "id": "B09", "type": "kho", "input": "Phường 4, Quận 3",
            "expected": "HỎI LẠI: phường Bàn Cờ, phường Xuân Hòa",
            "output": output, "pass": "",
            "ghi_chu": "hoi_mot_lan_du_y=0 thiếu phường Xuân Hòa",
        }
        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        try:
            for _ in range(2):
                with open(path, "w", encoding="utf-8-sig", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=list(row))
                    w.writeheader()
                    w.writerow(row)
                grade.cham_file(path)
                with open(path, encoding="utf-8-sig", newline="") as f:
                    row = list(csv.DictReader(f))[0]
        finally:
            os.remove(path)
        self.assertEqual(row["ghi_chu"].count("hoi_mot_lan_du_y="), 1)
        self.assertIn("thiếu phường Xuân Hòa", row["ghi_chu"])
        self.assertEqual(row["pass"], "0")
