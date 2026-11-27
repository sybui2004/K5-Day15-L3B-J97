"""Stub TẠM cho bốn công cụ X2 — XOÁ FILE NÀY khi `feature/cp3-x2-tools` đã merge.

agent.py chỉ import file này khi tools.py chưa có validate_phone… (X2 chưa merge), để
`python run.py` và test của X3 chạy được trong lúc chờ. Hợp đồng giống hệt X2 (docs/cp2-ke-hoach.md),
nhưng KHÔNG có bảng chuyển đổi: quy đổi luôn ra "khong_thay", tra phường luôn không khớp.
Không dùng file này để chấm hay demo.
"""
import hashlib
import json

from tracing import tool


@tool
def validate_phone(sdt: str) -> dict:
    """(stub) Kiểm sđt. Input: sđt (str). Output: {ok, sdt_chuan, ly_do}. Không tác động ra ngoài."""
    s = "".join(ch for ch in str(sdt) if ch.isdigit() or ch == "+")
    if s.startswith("+84"):
        s = "0" + s[3:]
    elif s.startswith("84") and len(s) == 11:
        s = "0" + s[2:]
    ok = len(s) == 10 and s[:2] in ("03", "05", "07", "08", "09")
    return {"ok": ok, "sdt_chuan": s if ok else None, "ly_do": "" if ok else "sđt phải đủ 10 số, đầu 03/05/07/08/09"}


@tool
def convert_old_address(tinh_thanh: str, quan_huyen_cu: str, phuong_xa_cu: str) -> dict:
    """(stub) Quy địa chỉ cũ sang phường mới. Chưa có bảng nên luôn "khong_thay". Không tác động ra ngoài."""
    return {"ket_qua": "khong_thay", "phuong_moi": []}


@tool
def lookup_address(tinh_thanh: str, phuong_xa: str) -> dict:
    """(stub) Tra phường mới. Chưa có bảng nên luôn không khớp. Không tác động ra ngoài."""
    return {"ok": False, "khop": None, "goi_y": [], "ly_do": "stub: chưa có bảng chuyển đổi (chờ X2)"}


@tool
def create_draft_order(info: dict) -> dict:
    """(stub) Tạo đơn nháp. Output: {ma_don, ma_van_don, trang_thai}. Chỉ bản nháp, không gọi GHN."""
    khoa = ["ten_nguoi_nhan", "sdt", "dia_chi_chi_tiet", "phuong_xa", "tinh_thanh", "san_pham", "so_luong", "ma_hoi_thoai"]
    raw = json.dumps({k: info.get(k) for k in khoa}, sort_keys=True, ensure_ascii=False)
    h = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8]
    return {"ma_don": "DN-" + h, "ma_van_don": "GHN-NHAP-" + h, "trang_thai": "cho_duyet"}
