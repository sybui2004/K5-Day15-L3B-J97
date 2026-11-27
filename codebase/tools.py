"""Công cụ của bài toán (X2): kiểm sđt, quy đổi và tra địa giới, tạo đơn nháp.

Mỗi công cụ là một hàm có @tool (khung tự ghi vào trace). Docstring ghi: tên · input · output · tác động ra ngoài.
Không công cụ nào gửi tin, ghi file hay gọi mạng: create_draft_order chỉ trả mã nháp chờ chủ shop duyệt.

Dữ liệu: data/chuyen-doi-dia-gioi.csv (X0, Nghị quyết 1685/NQ-UBTVQH15, xem data/DATA_CARD.md Dataset 2).
"""
import csv
import difflib
import functools
import hashlib
import json
import os
import re
import unicodedata

from tracing import tool, TOOLS  # noqa: F401  (TOOLS: danh sách công cụ đã đăng ký)

BANG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "chuyen-doi-dia-gioi.csv")
HCM = "TP Hồ Chí Minh"

# ---------- chuẩn hoá tên ----------

_TIEN_TO = ["thành phố", "thanh pho", "thị trấn", "thi tran", "thị xã", "thi xa", "đặc khu", "dac khu",
            "phường", "phuong", "xã", "xa", "quận", "quan", "huyện", "huyen", "tỉnh", "tinh", "tp"]
_TIEN_TO = sorted((t.split() for t in _TIEN_TO), key=len, reverse=True)
_DAU_CU = [("oà", "òa"), ("oá", "óa"), ("oả", "ỏa"), ("oã", "õa"), ("oạ", "ọa"),
           ("uỳ", "ùy"), ("uý", "úy"), ("uỷ", "ủy"), ("uỹ", "ũy"), ("uỵ", "ụy")]


def bo_dau(s):
    s = unicodedata.normalize("NFD", s).replace("đ", "d").replace("Đ", "D")
    return unicodedata.normalize("NFC", "".join(c for c in s if not unicodedata.combining(c)))


def _khoa(s):
    """Tên địa danh -> (khoá còn dấu, khoá không dấu). Bỏ một tiền tố loại đơn vị nếu là cả từ;
    'p'/'q' chỉ bỏ khi theo sau là chữ số hoặc dấu chấm (p7, p.07, q3, q.3) để 'Phú' không mất chữ P."""
    s = unicodedata.normalize("NFC", str(s or "")).lower()
    for a, b in _DAU_CU:
        s = s.replace(a, b)
    s = re.sub(r"\b[pq]\s*\.\s*", " ", s)
    s = re.sub(r"\b[pq](?=\s*[0-9])", " ", s)
    tu = re.sub(r"[\W_]+", " ", s).split()
    for tt in _TIEN_TO:
        if len(tu) > len(tt) and tu[:len(tt)] == tt:
            tu = tu[len(tt):]
            break
    # bỏ số 0 đầu ở token chữ số ASCII (p.07 = Phường 7). Không dùng isdigit()/int(): '²'.isdigit() là True
    # nhưng int('²') lỗi. Token khác giữ nguyên, để tra cứu trả "không khớp" thay vì ném ngoại lệ.
    tu = [(t.lstrip("0") or "0") if re.fullmatch(r"[0-9]+", t) else t for t in tu]
    co_dau = " ".join(tu)
    return co_dau, bo_dau(co_dau)


def chuan_hoa_ten(s):
    """Khoá không dấu để so tên (agent dùng khi so phường khách chọn với danh sách)."""
    return _khoa(s)[1]


def _co_dau(s):
    return bo_dau(str(s or "")) != str(s or "")


def _khop(ten, ung_vien):
    """So `ten` với danh sách tên chuẩn. Viết có dấu thì so khoá còn dấu trước (để 'Thanh An' khác 'Thạnh An'),
    rồi mới so không dấu. Trả list tên chuẩn khớp (0, 1 hoặc nhiều)."""
    k_dau, k_kd = _khoa(ten)
    if not k_kd:
        return []
    if _co_dau(ten):
        ra = [u for u in ung_vien if _khoa(u)[0] == k_dau]
        if ra:
            return ra
    return [u for u in ung_vien if _khoa(u)[1] == k_kd]


_TINH = {
    HCM: {"ho chi minh", "hcm", "tphcm", "hcmc", "sai gon", "sg"},
    "Bình Dương": {"binh duong"},
    "Bà Rịa - Vũng Tàu": {"ba ria vung tau", "brvt", "br vt", "vung tau", "ba ria"},
}


def chuan_hoa_tinh(s):
    """'tp hcm' / 'Sài Gòn' -> 'TP Hồ Chí Minh'; 'brvt' -> 'Bà Rịa - Vũng Tàu'; ngoài bảng -> None."""
    k = re.sub(r"[\W_]+", " ", bo_dau(str(s or "")).lower()).split()
    for tt in (["thanh", "pho"], ["tp"], ["tinh"]):
        if len(k) > len(tt) and k[:len(tt)] == tt:
            k = k[len(tt):]
            break
    k = " ".join(k)
    for ten, ds in _TINH.items():
        if k in ds:
            return ten
    return None


@functools.lru_cache(maxsize=1)
def _bang():
    with open(BANG, encoding="utf-8") as f:
        return tuple(csv.DictReader(f))


# ---------- công cụ ----------

@tool
def validate_phone(sdt: str) -> dict:
    """validate_phone · Input: sđt khách ghi (str, có thể có dấu cách, '.', '-', '+84').
    Output: {"ok": bool, "sdt_chuan": "0xxxxxxxxx" | None, "ly_do": str}.
    Hợp lệ khi đủ 10 chữ số, đầu 03/05/07/08/09. Không tác động ra ngoài."""
    s = re.sub(r"[\s.\-()]", "", str(sdt or ""))
    if s.startswith("+84"):
        s = "0" + s[3:]
    elif s.startswith("84"):
        s = "0" + s[2:]
    if not s:
        return {"ok": False, "sdt_chuan": None, "ly_do": "không có số điện thoại"}
    if not re.fullmatch(r"[0-9]+", s):  # không dùng isdigit(): nó nhận cả '²', '０', '٣'
        return {"ok": False, "sdt_chuan": None, "ly_do": "số điện thoại có ký tự không phải chữ số 0-9"}
    if len(s) != 10:
        return {"ok": False, "sdt_chuan": None, "ly_do": "số điện thoại phải đủ 10 chữ số (đang có %d)" % len(s)}
    if s[:2] not in ("03", "05", "07", "08", "09"):
        return {"ok": False, "sdt_chuan": None, "ly_do": "số di động phải bắt đầu bằng 03, 05, 07, 08 hoặc 09"}
    return {"ok": True, "sdt_chuan": s, "ly_do": ""}


@tool
def convert_old_address(tinh_thanh: str, quan_huyen_cu: str, phuong_xa_cu: str) -> dict:
    """convert_old_address · Input: tỉnh (TP HCM hoặc tỉnh cũ Bình Dương / Bà Rịa - Vũng Tàu), quận/huyện cũ,
    phường/xã cũ (str, viết tắt hay không dấu đều được).
    Output: {"ket_qua": "mot" | "nhieu" | "khong_thay", "phuong_moi": [tên phường mới], "tinh_moi": "TP Hồ Chí Minh" | None,
    "khoan": [số khoản Điều 1 NQ 1685], "ly_do": str}. "nhieu" = phường cũ bị tách: không tự chọn, phải hỏi khách.
    Chỉ đọc bảng. Không tác động ra ngoài."""
    rong = {"ket_qua": "khong_thay", "phuong_moi": [], "tinh_moi": None, "khoan": []}
    tinh = chuan_hoa_tinh(tinh_thanh)
    if not tinh:
        return dict(rong, ly_do="tỉnh/thành '%s' ngoài phạm vi bảng (chỉ TP Hồ Chí Minh, gồm Bình Dương, "
                                "Bà Rịa - Vũng Tàu cũ)" % tinh_thanh)
    if not str(quan_huyen_cu or "").strip():
        return dict(rong, ly_do="cần quận/huyện cũ")
    # tra quận/huyện trước, rồi mới xét phường
    dong = [r for r in _bang() if tinh == HCM or r["tinh_cu"] == tinh]
    quan = _khop(quan_huyen_cu, sorted({r["quan_huyen_cu"] for r in dong if r["quan_huyen_cu"]}))
    if len(quan) != 1:
        return dict(rong, ly_do="không thấy quận/huyện cũ '%s' ở %s" % (quan_huyen_cu, tinh))
    dong = [r for r in dong if r["quan_huyen_cu"] == quan[0]]
    phuong_trong = not str(phuong_xa_cu or "").strip()
    if all(not r["phuong_xa_cu"] for r in dong):
        # cả huyện sắp xếp thành một đơn vị (huyện Côn Đảo -> đặc khu Côn Đảo, khoản 163): huyện không có
        # phường/xã nên phường cũ để trống hoặc ghi lại tên huyện là hợp lệ; ghi một phường khác là mâu thuẫn
        if not phuong_trong and _khoa(phuong_xa_cu)[1] != _khoa(quan[0])[1]:
            return dict(rong, ly_do="%s không có phường/xã, '%s' không thuộc huyện này" % (quan[0], phuong_xa_cu))
        trung = dong
    else:
        if phuong_trong:
            return dict(rong, ly_do="cần phường/xã cũ thuộc %s" % quan[0])
        phuong = _khop(phuong_xa_cu, sorted({r["phuong_xa_cu"] for r in dong}))
        if len(phuong) > 1:
            return dict(rong, ly_do="'%s' khớp nhiều phường cũ ở %s: %s" % (phuong_xa_cu, quan[0], ", ".join(phuong)))
        trung = [r for r in dong if phuong and r["phuong_xa_cu"] == phuong[0]]
        if not trung:
            return dict(rong, ly_do="không thấy '%s' thuộc %s trong Nghị quyết 1685" % (phuong_xa_cu, quan[0]))
    trung.sort(key=lambda r: int(r["khoan"]))
    moi = list(dict.fromkeys(r["phuong_xa_moi"] for r in trung))
    return {"ket_qua": "mot" if len(moi) == 1 else "nhieu", "phuong_moi": moi, "tinh_moi": HCM,
            "khoan": sorted({int(r["khoan"]) for r in trung}),
            "ly_do": "" if len(moi) == 1 else "phường cũ bị tách, Nghị quyết không nói đường nào thuộc phần nào"}


@tool
def lookup_address(tinh_thanh: str, phuong_xa: str) -> dict:
    """lookup_address · Input: tỉnh (TP HCM hoặc tỉnh cũ), phường/xã kiểu mới (str).
    Output: {"ok": bool, "khop": tên chuẩn | None, "tinh": "TP Hồ Chí Minh" | None, "goi_y": [≤3 tên gần giống],
    "ly_do": str}. Tra trên tập phường/xã mới của bảng. Chỉ đọc bảng. Không tác động ra ngoài."""
    tinh = chuan_hoa_tinh(tinh_thanh)
    if not tinh:
        return {"ok": False, "khop": None, "tinh": None, "goi_y": [],
                "ly_do": "tỉnh/thành '%s' ngoài phạm vi bảng (chỉ TP Hồ Chí Minh)" % tinh_thanh}
    # khách ghi tỉnh cũ cụ thể -> chỉ xét phường/xã mới hình thành từ địa bàn tỉnh đó; ghi TP HCM -> cả bảng
    ds = sorted({r["phuong_xa_moi"] for r in _bang() if tinh == HCM or r["tinh_cu"] == tinh})
    trung = _khop(phuong_xa, ds)
    if len(trung) == 1:
        return {"ok": True, "khop": trung[0], "tinh": HCM, "goi_y": [], "ly_do": ""}
    if len(trung) > 1:
        return {"ok": False, "khop": None, "tinh": HCM, "goi_y": trung[:3],
                "ly_do": "'%s' khớp nhiều phường/xã: %s" % (phuong_xa, ", ".join(trung))}
    k = _khoa(phuong_xa)[1]
    theo_khoa = {}
    for u in ds:
        theo_khoa.setdefault(_khoa(u)[1], []).append(u)
    goi_y = [u for kk in difflib.get_close_matches(k, list(theo_khoa), n=3, cutoff=0.6) for u in theo_khoa[kk]][:3]
    pham_vi = "TP Hồ Chí Minh" if tinh == HCM else "TP Hồ Chí Minh trên địa bàn %s cũ" % tinh
    ly_do = "không thấy phường/xã '%s' trong danh sách phường/xã mới của %s" % (phuong_xa, pham_vi)
    if re.fullmatch(r"[0-9]+", k):
        ly_do += " (phường số là tên cũ: cần kèm quận/huyện cũ để quy đổi)"
    return {"ok": False, "khop": None, "tinh": HCM, "goi_y": goi_y, "ly_do": ly_do}


KHOA_MA = ["ten_nguoi_nhan", "sdt", "dia_chi_chi_tiet", "phuong_xa", "tinh_thanh", "san_pham", "so_luong",
           "ma_hoi_thoai"]


@tool
def create_draft_order(info: dict) -> dict:
    """create_draft_order · Input: thông tin đơn đã kiểm (dict, các khoá KHOA_MA; phuong_xa đã quy đổi).
    Output: {"ma_don": "DN-xxxxxxxx", "ma_van_don": "GHN-NHAP-xxxxxxxx", "trang_thai": "cho_duyet"}.
    Mã ổn định: sha1 của các trường KHOA_MA (sđt chuẩn hoá trước), không hash trường model tự viết.
    Tác động ra ngoài: KHÔNG — chỉ bản nháp chờ chủ shop duyệt, không ghi file, không gọi GHN."""
    du_lieu = {k: info.get(k) for k in KHOA_MA}
    if du_lieu["sdt"]:
        kq = validate_phone(du_lieu["sdt"])
        if kq["ok"]:
            du_lieu["sdt"] = kq["sdt_chuan"]
    h = hashlib.sha1(json.dumps(du_lieu, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:8]
    return {"ma_don": "DN-" + h, "ma_van_don": "GHN-NHAP-" + h, "trang_thai": "cho_duyet"}
