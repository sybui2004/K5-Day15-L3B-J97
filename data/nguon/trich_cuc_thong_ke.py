"""Trích phần TP Hồ Chí Minh từ bảng chuyển đổi ĐVHC mới–cũ của Cục Thống kê.

File gốc (cả nước, ~1,1 MB, không commit):
  https://danhmuchanhchinh.nso.gov.vn/TAPTIN/BangChuyendoiĐVHCmoi_cu_final.xlsx
  (link "Bảng chuyển đổi" trên trang https://danhmuchanhchinh.nso.gov.vn/)

Chạy: python data/nguon/trich_cuc_thong_ke.py <đường dẫn file .xlsx>
Ra:   data/nguon/cuc-thong-ke-hcm.csv  (sheet "Tổng hợp_không merge", chỉ các dòng tỉnh mới = TP Hồ Chí Minh)

Chỉ dùng thư viện chuẩn (đọc xlsx bằng zipfile + XML).
"""
import csv
import os
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "cuc-thong-ke-hcm.csv")
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
SHEET_NAME = "Tổng hợp_không merge"


def col_index(ref):
    n = 0
    for ch in re.match(r"[A-Z]+", ref).group():
        n = n * 26 + ord(ch) - 64
    return n - 1


def read_sheet(path, sheet_name):
    z = zipfile.ZipFile(path)
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(NS + "si"):
            shared.append("".join(t.text or "" for t in si.iter(NS + "t")))
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    names = [s.get("name").strip() for s in wb.iter(NS + "sheet")]
    idx = names.index(sheet_name.strip())
    root = ET.fromstring(z.read(f"xl/worksheets/sheet{idx + 1}.xml"))
    for row in root.iter(NS + "row"):
        vals = {}
        for c in row.iter(NS + "c"):
            v, t = c.find(NS + "v"), c.get("t")
            if t == "inlineStr":
                x = "".join(tt.text or "" for tt in c.iter(NS + "t"))
            elif v is None:
                continue
            elif t == "s":
                x = shared[int(v.text)]
            else:
                x = v.text
            vals[col_index(c.get("r"))] = x
        if vals:
            yield [vals.get(i, "") for i in range(max(vals) + 1)]


def main():
    src = sys.argv[1]
    out = []
    for r in read_sheet(src, SHEET_NAME):
        r = [re.sub(r"\s+", " ", unicodedata.normalize("NFC", x)).strip() for x in r] + [""] * 8
        if r[0].startswith("Thành phố Hồ Chí Minh (79)"):
            out.append(r[:8])
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["tinh_moi", "xa_moi", "ma_xa_moi", "xa_cu", "ma_xa_cu", "ghi_chu", "quan_huyen_cu", "tinh_cu"])
        w.writerows(out)
    print(f"{len(out)} dòng -> {OUT}")


if __name__ == "__main__":
    main()
