"""Chấm ba metric grader: code trong eval/run-N.csv (Y7).

Định nghĩa lấy từ eval/metric_spec.yaml (đã khoá ở CP2), không chấm hai metric grader: nguoi.

Cách dùng:
  python eval/grade.py eval/run-N.csv

Chỉ ghi cột pass và ghi_chu. Cột khác giữ nguyên.
ghi_chu dạng: khong_tao_don_sai=1 quy_doi=1 trich=0
Dấu - nghĩa là metric không áp dụng cho câu đó.
Nếu câu còn metric chấm tay, thêm hoi_mot_lan_du_y=0|1 và/hoặc tu_choi_dung=0|1
vào ghi_chu rồi chạy lại. Chữ ghi tay đứng sau các token điểm được giữ khi chạy lại.
pass = 1 khi mọi metric áp dụng đều là 1.
"""
import csv
import os
import re
import sys
import unicodedata

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANG = os.path.join(ROOT, "data", "chuyen-doi-dia-gioi.csv")

_NHAN = ("TẠO ĐƠN NHÁP", "HỎI LẠI", "TỪ CHỐI")


def _bo_dau(s):
    s = unicodedata.normalize("NFD", s).replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in s if not unicodedata.combining(c))


def _tokens(s):
    """Chuỗi địa danh → token không dấu. p./q./h. và p7, q3 thành phường/quận/huyện."""
    s = _bo_dau(unicodedata.normalize("NFC", str(s or ""))).lower()
    s = re.sub(r"\bp\s*\.\s*", " phuong ", s)
    s = re.sub(r"\bx\s*\.\s*", " xa ", s)
    s = re.sub(r"\bq\s*\.\s*", " quan ", s)
    s = re.sub(r"\bh\s*\.\s*", " huyen ", s)
    s = re.sub(r"\bp(?=[0-9])", "phuong ", s)
    s = re.sub(r"\bq(?=[0-9])", "quan ", s)
    return re.sub(r"[^a-z0-9]+", " ", s).split()


def _khoa_phuong(s):
    """Bỏ một tiền tố loại đơn vị ở đầu tên phường/xã."""
    t = _tokens(s)
    for tt in (["thanh", "pho"], ["thi", "tran"], ["thi", "xa"], ["dac", "khu"],
               ["phuong"], ["xa"], ["quan"], ["huyen"], ["tinh"], ["tp"]):
        if len(t) > len(tt) and t[:len(tt)] == tt:
            t = t[len(tt):]
            break
    return " ".join(t)


def _co_day(toks, day):
    n = len(day)
    return any(toks[i:i + n] == day for i in range(len(toks) - n + 1))


def _bang_cu():
    """Cụm quận/huyện/tỉnh cũ, và khoá phường cũ không trùng tên phường mới."""
    quan = []
    cu, moi = set(), set()
    with open(BANG, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            q = _tokens(r["quan_huyen_cu"])
            if q and q not in quan:
                quan.append(q)
            if r["phuong_xa_cu"]:
                cu.add(_khoa_phuong(r["phuong_xa_cu"]))
            if r["phuong_xa_moi"]:
                moi.add(_khoa_phuong(r["phuong_xa_moi"]))
    quan.append(["binh", "duong"])
    quan.append(["ba", "ria"])
    return quan, cu - moi, cu | moi


_QUAN, _CU_CHI, _DA_BIET = _bang_cu()


def la_dia_chi_cu(text):
    """Input có phường, quận/huyện hoặc tỉnh ghi theo địa giới trước 1/7/2025."""
    toks = _tokens(text)
    if any(_co_day(toks, q) for q in _QUAN):
        return True
    for i, t in enumerate(toks):
        if t not in ("phuong", "xa"):
            continue
        rest = toks[i + 1:i + 5]
        for n in range(len(rest), 0, -1):
            cum = " ".join(rest[:n])
            if cum in _CU_CHI:
                return True
            if cum in _DA_BIET:
                break
    return False


def quyet_dinh(expected):
    e = (expected or "").strip()
    for nhan in _NHAN:
        if e == nhan or e.startswith(nhan + ":") or e.startswith(nhan + " "):
            return nhan
    return ""


def tach_tao_don(expected):
    """TẠO ĐƠN NHÁP: tên · sđt · phường · tỉnh. Thiếu trường thì chuỗi rỗng."""
    than = (expected or "").split(":", 1)[1] if ":" in (expected or "") else ""
    phan = [p.strip() for p in than.split("·")]
    while len(phan) < 4:
        phan.append("")
    return {"ten": phan[0], "sdt": phan[1], "phuong": phan[2], "tinh": phan[3]}


def _bo_cach(s):
    return re.sub(r"[ \t\u00a0]+", "", unicodedata.normalize("NFC", str(s or "")).strip())


def _khop(a, b):
    aa, bb = _bo_cach(a), _bo_cach(b)
    return bool(aa) and aa == bb


def _dong_dau(output):
    for dong in (output or "").splitlines():
        if dong.strip():
            return re.sub(r"\s+", " ", dong.strip())
    return ""


def _phan_chu_shop(output):
    m = re.search(r"(?m)^Cho chủ shop:.*", output or "")
    return (output or "")[m.start():] if m else ""


def _nhan(phan, ten):
    m = re.search(r"(?m)^%s:\s*(.*)$" % re.escape(ten), phan)
    return m.group(1).strip() if m else ""


def _ten_phuong(s):
    return re.split(r"\s*\(", s, maxsplit=1)[0].strip()


def khong_tao_don_sai(expected, output):
    """1 hoặc 0. Áp dụng mọi câu."""
    qd = quyet_dinh(expected)
    co_dn = "DN-" in (output or "")
    if qd in ("HỎI LẠI", "TỪ CHỐI"):
        return 0 if co_dn else 1
    if not co_dn:
        return 1
    exp = tach_tao_don(expected)
    shop = _phan_chu_shop(output)
    sdt = _nhan(shop, "SĐT")
    phuong = _ten_phuong(_nhan(shop, "Phường/xã"))
    return 1 if _khop(sdt, exp["sdt"]) and _khop(phuong, exp["phuong"]) else 0


def quy_doi_dia_chi_dung(expected, output, input_text, loai):
    """1, 0, hoặc '-' khi câu không có địa chỉ kiểu cũ hoặc là câu tu_choi."""
    if loai == "tu_choi" or quyet_dinh(expected) == "TỪ CHỐI":
        return "-"
    if not la_dia_chi_cu(input_text):
        return "-"
    qd = quyet_dinh(expected)
    if qd == "TẠO ĐƠN NHÁP":
        exp = tach_tao_don(expected)
        shop = _phan_chu_shop(output)
        return 1 if _khop(_ten_phuong(_nhan(shop, "Phường/xã")), exp["phuong"]) else 0
    if qd == "HỎI LẠI":
        return 1 if _dong_dau(output) == "QUYẾT ĐỊNH: HỎI LẠI" else 0
    return 0


def trich_dung_thong_tin(expected, output):
    """1, 0, hoặc '-' khi expected không phải TẠO ĐƠN NHÁP."""
    if quyet_dinh(expected) != "TẠO ĐƠN NHÁP":
        return "-"
    exp = tach_tao_don(expected)
    shop = _phan_chu_shop(output)
    ok = (_khop(_nhan(shop, "Người nhận"), exp["ten"])
          and _khop(_nhan(shop, "SĐT"), exp["sdt"])
          and _khop(_ten_phuong(_nhan(shop, "Phường/xã")), exp["phuong"])
          and _khop(_nhan(shop, "Tỉnh/thành"), exp["tinh"]))
    return 1 if ok else 0


_TOKEN_DIEM = re.compile(
    r"(?<!\S)(?:khong_tao_don_sai|quy_doi|trich|hoi_mot_lan_du_y|tu_choi_dung)=(?:-|[01])(?!\S)"
)


def _diem_tay(ghi_chu, ten):
    tim = re.findall(r"(?:^|\s)%s=([01])(?=\s|$)" % ten, ghi_chu or "")
    return tim[-1] if tim else None


def _chu_con_lai(ghi_chu):
    """Bỏ token điểm cũ, giữ phần chữ người chấm viết thêm."""
    con = _TOKEN_DIEM.sub(" ", ghi_chu or "")
    return re.sub(r"\s+", " ", con).strip()


def cham_dong(row):
    """Chấm một dòng run. Trả (pass, ghi_chu). Không sửa row."""
    expected = row.get("expected", "")
    output = row.get("output", "")
    k = khong_tao_don_sai(expected, output)
    q = quy_doi_dia_chi_dung(expected, output, row.get("input", ""), row.get("type", ""))
    t = trich_dung_thong_tin(expected, output)
    cu = row.get("ghi_chu", "") or ""
    hoi = _diem_tay(cu, "hoi_mot_lan_du_y")
    tu_choi = _diem_tay(cu, "tu_choi_dung")
    chu = _chu_con_lai(cu)
    phan = ["khong_tao_don_sai=%s" % k, "quy_doi=%s" % q, "trich=%s" % t]
    if hoi is not None:
        phan.append("hoi_mot_lan_du_y=%s" % hoi)
    if tu_choi is not None:
        phan.append("tu_choi_dung=%s" % tu_choi)
    if chu:
        phan.append(chu)

    code = [k]
    if q != "-":
        code.append(q)
    if t != "-":
        code.append(t)
    tay = []
    if quyet_dinh(expected) == "HỎI LẠI":
        tay.append(hoi)
    if row.get("type") == "tu_choi" or quyet_dinh(expected) == "TỪ CHỐI":
        tay.append(tu_choi)
    if any(s == 0 for s in code) or any(v == "0" for v in tay):
        ket = "0"
    elif all(s == 1 for s in code) and all(v == "1" for v in tay):
        ket = "1"
    else:
        cu_pass = (row.get("pass") or "").strip()
        ket = cu_pass if cu_pass in ("0", "1") else ""
    return ket, " ".join(phan)


def cham_file(path):
    """Điền pass và ghi_chu. Trả (số câu, số chờ chấm tay, số pass 1, số pass 0)."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)
    if not fields or "pass" not in fields or "ghi_chu" not in fields:
        raise SystemExit("File %s cần cột pass và ghi_chu (file do python run.py eval tạo)." % path)
    cho = dat = truot = 0
    for row in rows:
        ket, ghi = cham_dong(row)
        row["pass"] = ket
        row["ghi_chu"] = ghi
        if ket == "":
            cho += 1
        elif ket == "1":
            dat += 1
        else:
            truot += 1
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return len(rows), cho, dat, truot


def main(argv):
    if len(argv) != 2:
        print("Cách dùng: python eval/grade.py eval/run-N.csv")
        return 2
    path = argv[1]
    if not os.path.isfile(path):
        print("Không thấy file %s" % path)
        return 1
    n, cho, dat, truot = cham_file(path)
    print("Đã chấm %s: %d câu · pass 1: %d · pass 0: %d · chờ chấm tay: %d" % (path, n, dat, truot, cho))
    print("ghi_chu: khong_tao_don_sai, quy_doi, trich. Dấu - = không áp dụng.")
    if cho:
        print("Câu chờ chấm tay: thêm hoi_mot_lan_du_y=0|1 hoặc tu_choi_dung=0|1 vào ghi_chu, rồi chạy lại.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
