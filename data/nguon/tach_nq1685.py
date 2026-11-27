"""Tách Điều 1 Nghị quyết 1685/NQ-UBTVQH15 thành bảng địa giới cũ -> mới.

Chạy: python data/nguon/tach_nq1685.py
Vào : data/nguon/nq1685-dieu1.txt     (Điều 1 chép nguyên văn — nguồn chính: phường cũ, phường mới, kiểu, khoản)
      data/nguon/cuc-thong-ke-hcm.csv (bảng chuyển đổi của Cục Thống kê — chỉ để tra quận/huyện, tỉnh cũ
                                        khi văn bản không ghi, và đối chiếu chéo)
Ra  : data/chuyen-doi-dia-gioi.csv + báo cáo lệch in ra màn hình

Luật:
- Phường cũ, phường mới, kiểu (toan_bo / mot_phan / phan_con_lai), khoản: chỉ lấy từ văn bản.
- quan_huyen_cu: văn bản ghi ngay sau tên (vd "Phường 4 (Quận 3)", hoặc dãy "Phường 8 và Phường 9 (Quận 4)")
  -> nguon_quan=van_ban. Còn lại tra Cục Thống kê theo cặp (phường mới, phường cũ) -> nguon_quan=cuc_thong_ke.
  Không tra được -> để trống, nguon_quan=chua_ro (không đoán).
- tinh_cu: theo Cục Thống kê (cột "Tỉnh cũ").
- Khoản 164: 05 đơn vị không sắp xếp, ghi kieu=khong_sap_xep (tên cũ = tên mới).
Chỉ dùng thư viện chuẩn.
"""
import csv, os, re, sys, unicodedata, collections

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
TEXT = os.path.join(HERE, "nq1685-dieu1.txt")
NSO = os.path.join(HERE, "cuc-thong-ke-hcm.csv")
OUT = os.path.join(os.path.dirname(HERE), "chuyen-doi-dia-gioi.csv")

NSO_TAG = "cuc_thong_ke"


def nfc(s):
    return unicodedata.normalize("NFC", s)


def key(s):
    s = nfc(s).casefold().strip()
    # gom cách đặt dấu kiểu cũ/mới (hoà/hòa, thuý/thúy...)
    for a, b in [("oà", "òa"), ("oá", "óa"), ("oả", "ỏa"), ("oã", "õa"), ("oạ", "ọa"),
                 ("uý", "úy"), ("uỳ", "ùy"), ("uỷ", "ủy"), ("uỹ", "ũy"), ("uỵ", "ụy")]:
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s)


def fmt_quan(nso_name):
    """'Quận Phú Nhuận (768)' -> 'quận Phú Nhuận'; 'Quận 3 (770)' -> 'Quận 3' (giống cách văn bản viết)."""
    n = re.sub(r"\s*\(\d+\)\s*$", "", nso_name).strip()
    m = re.match(r"(Quận|Huyện|Thành phố|Thị xã)\s+(.*)", n)
    if not m:
        return n
    loai, ten = m.groups()
    if loai == "Quận" and re.fullmatch(r"\d+", ten):
        return f"Quận {ten}"
    return f"{loai.lower()} {ten}"


def fmt_tinh(nso_name):
    n = re.sub(r"\s*\(\d+\)\s*$", "", nso_name).strip()
    return {"Thành phố Hồ Chí Minh": "TP Hồ Chí Minh", "Tỉnh Bình Dương": "Bình Dương",
            "Tỉnh Bà Rịa - Vũng Tàu": "Bà Rịa - Vũng Tàu"}[n]


# ---------- đọc bảng Cục Thống kê ----------
nso = {}            # (key mới, key cũ) -> (quận, tỉnh, ghi chú)
nso_by_new = collections.defaultdict(list)
quan_tinh = {}      # key quận -> tỉnh
_nso_rows = csv.reader(open(NSO, encoding="utf-8"))
next(_nso_rows)  # tiêu đề
for r in _nso_rows:
    _, moi, _, cu, _, ghichu, quan, tinh = r
    moi = re.sub(r"\s+", " ", moi).strip()
    nso[(key(moi), key(cu))] = (fmt_quan(quan), fmt_tinh(tinh), ghichu)
    nso_by_new[key(moi)].append(cu)
    quan_tinh[key(fmt_quan(quan))] = fmt_tinh(tinh)

# ---------- đọc Điều 1 ----------
lines = nfc(open(TEXT, encoding="utf-8").read()).split("\n")
khoan = {}
in_d1 = False
for ln in lines:
    if ln.startswith("Điều 1."):
        in_d1 = True
        continue
    if ln.startswith("Điều 2."):
        break
    m = re.match(r"(\d+)\.\s+(.*)", ln)
    if in_d1 and m:
        khoan[int(m.group(1))] = nfc(m.group(2))

MARK = re.compile(
    r"(toàn bộ diện tích tự nhiên, quy mô dân số của"
    r"|một phần diện tích tự nhiên, quy mô dân số của"
    r"|một phần diện tích tự nhiên, quy mô dân của"
    r"|một phần diện tích tự nhiên của"
    r"|một phần diện tích, quy mô dân số của"
    r"|phần còn lại của)"
)
KIEU = lambda mk: "toan_bo" if mk.startswith("toàn bộ") else ("mot_phan" if mk.startswith("một phần") else "phan_con_lai")
SAU_KHI = re.compile(r"\s*sau khi sắp xếp theo quy định tại khoản [\d, khoản]+(?:của )?Điều này")
TYPE_RE = re.compile(r"^(?:(các)\s+)?(phường|xã|thị trấn)\s+(.*)$")

rows, report = [], []
for k in sorted(khoan):
    t = khoan[k]
    if k == 164:
        continue
    m = re.match(r"(?:Sắp xếp|Nhập)\s+(.*)\s+thành (?:(phường|xã) mới|đặc khu) có tên gọi là (.+?)\.$", t)
    if not m:
        report.append(f"KHÔNG TÁCH ĐƯỢC khoản {k}: {t}")
        continue
    body, _, moi = m.groups()
    moi = moi.strip()
    if k == 163:  # huyện Côn Đảo -> đặc khu Côn Đảo: đơn vị cũ là cả huyện
        q, tinh, _ = nso.get((key(moi), key("")), ("huyện Côn Đảo", "Bà Rịa - Vũng Tàu", ""))
        rows.append(dict(tinh_cu=tinh, quan_huyen_cu="huyện Côn Đảo", phuong_xa_cu="",
                         phuong_xa_moi=moi, kieu="toan_bo", khoan=k, nguon_quan="van_ban"))
        continue
    body = SAU_KHI.sub("", body)
    parts = MARK.split(body)
    # parts: [trước marker đầu, marker, đoạn, marker, đoạn, ...]
    if parts[0].strip():
        report.append(f"khoản {k}: text trước marker đầu: {parts[0]!r}")
    units = []  # (tên, kiểu, quận văn bản hoặc None)
    for i in range(1, len(parts), 2):
        kieu = KIEU(parts[i])
        seg = parts[i + 1].strip().rstrip(",").strip()
        seg = re.sub(r"\s+và\s*$", "", seg)
        # tách từng đơn vị: dấu phẩy và chữ "và"
        toks = [x.strip() for x in re.split(r",|\s+và\s+", seg) if x.strip()]
        cur_type = None
        seg_units = []
        for tok in toks:
            ann = None
            ma = re.match(r"^(.*?)\s*\(([^)]*)\)\s*$", tok)
            if ma:
                tok, ann = ma.group(1).strip(), ma.group(2).strip()
            tok = re.sub(r"^phường\s+(Phường \d+)$", r"\1", tok)  # 'phường Phường 4' (khoản 22)
            if re.fullmatch(r"Phường \d+", tok):
                name = tok
                cur_type = "phường"
            else:
                mt = TYPE_RE.match(tok)
                if mt:
                    cur_type = mt.group(2)
                    name = f"{cur_type} {mt.group(3)}"
                elif cur_type:
                    name = f"{cur_type} {tok}"
                else:
                    report.append(f"khoản {k}: không rõ loại đơn vị: {tok!r}")
                    name = tok
            seg_units.append([name, kieu, None])
            if ann:
                seg_units[-1][2] = ann
                # quận ghi sau danh sách "Phường a, Phường b và Phường c (X)" áp cho cả dãy Phường số liền trước
                j = len(seg_units) - 2
                if re.fullmatch(r"Phường \d+", name):
                    while j >= 0 and seg_units[j][2] is None and re.fullmatch(r"Phường \d+", seg_units[j][0]):
                        seg_units[j][2] = ann
                        j -= 1
        units.extend(seg_units)

    for name, kieu, ann in units:
        hit = nso.get((key(moi), key(name)))
        if ann:
            quan, nguon = ann, "van_ban"
            if hit and key(hit[0]) != key(ann):
                report.append(f"LỆCH QUẬN khoản {k}: {name} -> văn bản '{ann}', Cục TK '{hit[0]}'")
        elif hit:
            quan, nguon = hit[0], NSO_TAG
        else:
            quan, nguon = "", "chua_ro"
            report.append(f"CHƯA RÕ QUẬN khoản {k}: {name} -> {moi}")
        tinh = hit[1] if hit else quan_tinh.get(key(quan), "")
        if not tinh:
            report.append(f"CHƯA RÕ TỈNH khoản {k}: {name}")
        if hit:
            nso_kieu = "toan_bo" if hit[2].startswith("Nhập toàn bộ") else "mot_phan_hoac_con_lai"
            if (kieu == "toan_bo") != (nso_kieu == "toan_bo"):
                report.append(f"LỆCH KIỂU khoản {k}: {name} -> {moi}: NQ '{kieu}', Cục TK '{hit[2]}'")
        rows.append(dict(tinh_cu=tinh, quan_huyen_cu=quan, phuong_xa_cu=name, phuong_xa_moi=moi,
                         kieu=kieu, khoan=k, nguon_quan=nguon))

# khoản 164: 05 đơn vị không thực hiện sắp xếp -> giữ nguyên tên
t164 = khoan[164]
m = re.search(r"không thực hiện sắp xếp là (.*)\.$", t164)
toks = [x.strip() for x in re.split(r",|\s+và\s+", m.group(1)) if x.strip()]
cur = None
for tok in toks:
    mt = TYPE_RE.match(tok)
    if mt:
        cur = mt.group(2)
        name = f"{cur} {mt.group(3)}"
    else:
        name = f"{cur} {tok}"
    hit = nso.get((key(name), key(name)))
    rows.append(dict(tinh_cu=hit[1] if hit else "", quan_huyen_cu=hit[0] if hit else "",
                     phuong_xa_cu=name, phuong_xa_moi=name, kieu="khong_sap_xep", khoan=164,
                     nguon_quan=NSO_TAG if hit else "chua_ro"))
    if not hit:
        report.append(f"CHƯA RÕ QUẬN khoản 164: {name}")

# ---------- đối chiếu chéo toàn bộ với Cục Thống kê ----------
ours = {(key(r["phuong_xa_moi"]), key(r["phuong_xa_cu"])) for r in rows}
for kk, v in nso.items():
    if kk not in ours:
        report.append(f"CỤC TK CÓ, NQ KHÔNG: mới={kk[0]} cũ={kk[1]} ({v})")
for r in rows:
    if (key(r["phuong_xa_moi"]), key(r["phuong_xa_cu"])) not in nso:
        report.append(f"NQ CÓ, CỤC TK KHÔNG: khoản {r['khoan']} {r['phuong_xa_cu']} -> {r['phuong_xa_moi']}")

cols = ["tinh_cu", "quan_huyen_cu", "phuong_xa_cu", "phuong_xa_moi", "kieu", "khoan", "nguon_quan"]
with open(OUT, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)

moi_set = {r["phuong_xa_moi"] for r in rows if r["kieu"] != "khong_sap_xep"}
print("số khoản:", len({r['khoan'] for r in rows}), "| số dòng:", len(rows))
print("đơn vị mới (Điều 1, khoản 1-163):", len(moi_set),
      collections.Counter(n.split()[0] if not n.startswith("đặc") else "đặc khu" for n in moi_set))
print("kiểu:", collections.Counter(r["kieu"] for r in rows))
print("nguon_quan:", collections.Counter(r["nguon_quan"] for r in rows))
print("tinh_cu:", collections.Counter(r["tinh_cu"] for r in rows))
print("--- báo cáo ---")
print("\n".join(report) or "(không có)")
