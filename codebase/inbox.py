"""Luồng A · hộp thư nhiều khách (task P1, docs/cp2-ke-hoach.md).

Cùng một quyết định AI như luồng chính: mỗi hội thoại đi qua agent.xu_ly, ở đây chỉ gom và sắp xếp.
    doc_hop_thu(path) -> list[{"ma_hoi_thoai", "ma_khach", "text"}]
    xu_ly_hop_thu(hoi_thoai) -> list[{"ma_hoi_thoai", **xu_ly(text, ma_hoi_thoai)}]
Không gửi tin, không ghi file: kết quả chờ chủ shop duyệt (màn hình duyệt, P2).
"""
import json
import os
import re

from agent import lam_sach_luot, xu_ly
from tracing import note

HOP_THU_MAU = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "hop-thu-mau.jsonl")
VAI = {"khach": "Khách", "shop": "Shop"}
THU_TU = {"TAO_DON_NHAP": 0, "HOI_LAI": 1, "TU_CHOI": 2}  # đơn chờ duyệt lên đầu


def _dung_text(dong: dict) -> str:
    """Ghép hội thoại theo 1.3 (a). Mã khách chỉ lấy từ trường `ma_khach` của hộp thư, không lấy từ lời nhắn."""
    phan = []
    ma_khach = dong.get("ma_khach")
    if ma_khach:
        if not re.fullmatch(r"KH-[0-9]+", ma_khach):
            raise ValueError("ma_khach không đúng dạng KH-<số>: %r" % ma_khach)
        phan.append("Mã khách: " + ma_khach)
    for luot in dong["luot"]:
        if luot["vai"] not in VAI:
            raise ValueError("vai phải là 'khach' hoặc 'shop', đang là %r" % luot["vai"])
        phan.append("%s: %s" % (VAI[luot["vai"]], lam_sach_luot(luot["tin"])))
    return " | ".join(phan)


def doc_hop_thu(path: str = HOP_THU_MAU) -> list:
    """Đọc file .jsonl, mỗi dòng {"ma_hoi_thoai", "ma_khach", "luot": [{"vai", "tin"}]}. Bỏ qua dòng trống."""
    ra = []
    with open(path, encoding="utf-8") as f:
        for so, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                dong = json.loads(line)
                ra.append({"ma_hoi_thoai": dong["ma_hoi_thoai"], "ma_khach": dong.get("ma_khach"),
                           "text": _dung_text(dong)})
            except (ValueError, KeyError, TypeError) as e:
                raise ValueError("%s, dòng %d: %s" % (os.path.basename(path), so, e)) from e
    return ra


def _ket_qua_loi(e: Exception) -> dict:
    """Cùng hình dạng với xu_ly (1.3 (e)). Không soạn tin gửi khách: lỗi là của hệ thống, shop xử lý tay."""
    ly_do = "lỗi xử lý: %s: %s" % (type(e).__name__, e)
    return {"quyet_dinh": "HOI_LAI", "truong": {}, "loi": [{"truong": "tat_ca", "ly_do": ly_do}],
            "goi_y_phuong": [], "tin_gui_khach": "",
            "cho_chu_shop": "Cho chủ shop: %s · shop xử lý tay hội thoại này · chưa tạo đơn nháp" % ly_do,
            "ma_don": None, "ma_van_don": None}


def xu_ly_hop_thu(hoi_thoai: list) -> list:
    """Xử lý từng hội thoại; một hội thoại lỗi không làm dừng cả hộp thư.
    Thứ tự ra: TẠO ĐƠN NHÁP, rồi HỎI LẠI, rồi TỪ CHỐI; trong mỗi nhóm giữ thứ tự vào."""
    ra = []
    for h in hoi_thoai:
        try:
            kq = xu_ly(h["text"], h["ma_hoi_thoai"])
        except Exception as e:  # model lỗi, mất mạng…
            note("hộp thư: hội thoại %s lỗi %s" % (h.get("ma_hoi_thoai"), type(e).__name__))
            kq = _ket_qua_loi(e)
        ra.append({"ma_hoi_thoai": h.get("ma_hoi_thoai"), **kq})
    return sorted(ra, key=lambda r: THU_TU[r["quyet_dinh"]])  # sorted giữ thứ tự trong cùng nhóm
