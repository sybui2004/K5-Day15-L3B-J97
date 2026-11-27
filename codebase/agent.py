"""Luồng chính: hội thoại chốt đơn → TẠO ĐƠN NHÁP / HỎI LẠI / TỪ CHỐI (task X3).

Hình dạng: workflow cố định 3 bước, đúng sơ đồ spec.md §4.
    Bước 1 · model đọc hội thoại, trả MỘT object JSON (1 lần gọi model).
    Bước 2 · code kiểm theo thứ tự docs/cp2-ke-hoach.md mục 1.3 (d), gom mọi lỗi.
    Bước 3 · đủ và chắc → create_draft_order (chỉ bản nháp); không thì HỎI LẠI một tin gom đủ.

Hợp đồng:
    xu_ly(text, ma_hoi_thoai=None) -> dict theo 1.3 (e) — hộp thư (A) và màn hình duyệt (D) dùng.
    answer(text) -> {"output": str} theo 1.3 (c) — `run.py`, eval, simulate dùng.

Tin hỏi lại là câu mẫu do code ghép từ lỗi đã gom, không gọi model lần hai.
Luồng C (giao chỗ cũ) chưa làm ở đây: P3 thêm bước 3 vào chỗ đánh dấu "LUỒNG C".
"""
import json
import re

from ai import call_model
from tracing import note

from tools import validate_phone, convert_old_address, lookup_address, create_draft_order, chuan_hoa_tinh, chuan_hoa_ten

SYSTEM = """Bạn đọc một đoạn chat giữa shop bán lẻ và khách đã đồng ý mua, rồi trích thông tin nhận hàng.
Chỉ trả MỘT object JSON, không viết gì khác, đúng các khoá sau (không có thì để null):
ten_nguoi_nhan, sdt, dia_chi_chi_tiet, tinh_thanh, phuong_xa, quan_huyen_cu, phuong_xa_cu,
san_pham, so_luong, dung_dia_chi_lan_truoc, yeu_cau_ngoai_pham_vi.

Quy tắc:
- Không đoán trường không có trong hội thoại. Thiếu thì để null.
- ten_nguoi_nhan, sdt là của người NHẬN hàng; người nhận khác người nhắn thì lấy người nhận.
- Khách đổi thông tin giữa chừng thì lấy lượt mới nhất.
- dia_chi_chi_tiet: số nhà, tên đường, thôn.
- tinh_thanh: ghi NHƯ KHÁCH VIẾT, kể cả tỉnh cũ, vd "TP Hồ Chí Minh", "Bình Dương", "Bà Rịa - Vũng Tàu".
- Khách ghi địa chỉ KIỂU MỚI (không có quận/huyện) thì điền phuong_xa.
- Khách ghi KIỂU CŨ (có quận/huyện) thì điền quan_huyen_cu và phuong_xa_cu, viết đầy đủ, vd "Quận 3", "Phường 4",
  "thành phố Thuận An".
- Không tự chọn phường mới. phuong_xa chỉ ghi tên phường/xã mới do chính khách viết hoặc khách đã chọn.
- Shop đã đưa danh sách phường và khách đã chọn một phường thì ghi tên phường đó vào phuong_xa.
- so_luong là số nguyên.
- dung_dia_chi_lan_truoc: true khi khách nói "giao chỗ cũ", "như lần trước".
- yeu_cau_ngoai_pham_vi: chép ngắn câu khách đòi việc KHÔNG phải lên một đơn mới. Gồm:
  đòi bỏ qua kiểm tra hoặc tạo đơn khi chưa đủ thông tin; đổi giá, xin bớt giá; hỏi tên, sđt, địa chỉ của khách khác;
  khiếu nại đơn cũ (giao trễ, giao sai, thái độ nhân viên), hàng hoàn chưa được lấy;
  xin sđt hoặc tên shipper, nhân viên giao hàng; hỏi địa chỉ bưu cục, kho, cửa hàng; đổi trả, hoàn tiền.
  Tin có lời phàn nàn nhưng khách VẪN đặt đơn mới và đưa thông tin nhận hàng thì đó là đơn: để null, trích như bình thường.
  Khách nhắc mã khách hoặc "địa chỉ lần trước" để giao cho chính mình là đặt đơn: để null.
  Không có thì null."""

BAT_BUOC = ["ten_nguoi_nhan", "sdt", "dia_chi_chi_tiet", "tinh_thanh", "san_pham", "so_luong"]
TEN_TRUONG = {  # tên trường → cách nói với khách
    "ten_nguoi_nhan": "tên người nhận",
    "sdt": "số điện thoại người nhận",
    "dia_chi_chi_tiet": "số nhà, tên đường",
    "tinh_thanh": "tỉnh/thành phố",
    "phuong_xa": "phường/xã",
    "quan_huyen_cu": "quận/huyện cũ của địa chỉ",
    "san_pham": "sản phẩm anh/chị muốn lấy",
    "so_luong": "số lượng",
}
NHAN_NGAN = {"ten_nguoi_nhan": "tên", "sdt": "sđt", "dia_chi_chi_tiet": "địa chỉ", "tinh_thanh": "tỉnh",
             "phuong_xa": "phường/xã", "quan_huyen_cu": "quận/huyện cũ",
             "san_pham": "sản phẩm", "so_luong": "số lượng", "dia_chi": "địa chỉ"}


# ---------- chuẩn hoá ----------

def lam_sach_luot(s: str) -> str:
    """Một lượt chat trên một dòng, không chứa ` | ` (docs/cp2-ke-hoach.md 1.3 (a))."""
    return " ".join(str(s).replace("|", " ").split())


def doc_ma_khach(text: str):
    """Mã tài khoản chat, chỉ đọc ở đoạn trước ` | ` đầu tiên. Mã nằm trong lượt `Khách:` thì bỏ qua."""
    dau = text.split("|", 1)[0]
    m = re.match(r"^\s*Mã khách:\s*(KH-\d+)\s*$", dau)
    return m.group(1) if m else None


def doc_json(text: str):
    """Lấy object JSON từ câu trả lời của model; hỏng thì None."""
    if not isinstance(text, str):
        return None
    t = re.sub(r"```(?:json)?", "", text)
    a, b = t.find("{"), t.rfind("}")
    if a < 0 or b <= a:
        return None
    try:
        obj = json.loads(t[a:b + 1])
    except ValueError:
        return None
    return obj if isinstance(obj, dict) else None


def _co(v) -> bool:
    return v is not None and not (isinstance(v, str) and not v.strip())


def _chuoi(v):
    return str(v).strip() if _co(v) else None


def _so_luong(v):
    """Trả (giá trị int hoặc None, lỗi hoặc None)."""
    if isinstance(v, bool):
        return None, "phải là số nguyên từ 1"
    if isinstance(v, str) and re.fullmatch(r"[0-9]+", v.strip()):  # không dùng isdigit(): nó nhận cả '²'
        v = int(v.strip())
    if not isinstance(v, int):
        return None, "phải là số nguyên từ 1"
    if v < 1:
        return None, "phải là số nguyên từ 1"
    return v, None


# ---------- bước 2: kiểm ----------

def _kiem(info: dict, text: str):
    """Kiểm theo 1.3 (d) bước 4–6. Trả (truong đã chuẩn hoá, loi, goi_y_phuong, quy_doi)."""
    truong = {k: info.get(k) for k in info}
    for k in ("ten_nguoi_nhan", "sdt", "dia_chi_chi_tiet", "tinh_thanh", "phuong_xa", "quan_huyen_cu",
              "phuong_xa_cu", "san_pham"):
        truong[k] = _chuoi(info.get(k))
    loi, goi_y, quy_doi = [], [], None

    # LUỒNG C (P3): dung_dia_chi_lan_truoc → get_customer_history(doc_ma_khach(text)) đặt ở đây, trước bước 4.

    # Bước 4 · thiếu trường bắt buộc
    for k in BAT_BUOC:
        if k == "so_luong":
            continue
        if not truong[k]:
            loi.append({"truong": k, "ly_do": "thiếu"})
    # huyện không có phường/xã cũ (Côn Đảo): công cụ quy đổi được chỉ với tên huyện
    ca_huyen = False
    quan, phuong_cu = truong["quan_huyen_cu"], truong["phuong_xa_cu"]
    if truong["tinh_thanh"] and quan and (chuan_hoa_ten(phuong_cu) == chuan_hoa_ten(quan) if phuong_cu
                                          else not truong["phuong_xa"]):
        ca_huyen = convert_old_address(truong["tinh_thanh"], quan, "")["ket_qua"] == "mot"
    if ca_huyen:
        truong["phuong_xa_cu"] = None
    kieu_cu = ca_huyen or bool(truong["phuong_xa_cu"])
    if kieu_cu and not truong["quan_huyen_cu"]:
        loi.append({"truong": "quan_huyen_cu", "ly_do": "thiếu"})
    if not kieu_cu and not truong["phuong_xa"]:
        loi.append({"truong": "phuong_xa", "ly_do": "thiếu"})
    if not _co(info.get("so_luong")):
        loi.append({"truong": "so_luong", "ly_do": "thiếu"})
        truong["so_luong"] = None
    else:
        sl, ly_do = _so_luong(info.get("so_luong"))
        truong["so_luong"] = sl
        if ly_do:
            loi.append({"truong": "so_luong", "ly_do": ly_do})

    # Bước 5 · sđt (chỉ khi có giá trị)
    if truong["sdt"]:
        kq = validate_phone(truong["sdt"])
        if not kq.get("ok"):
            loi.append({"truong": "sdt", "ly_do": kq.get("ly_do") or "không hợp lệ"})
        else:
            truong["sdt"] = kq["sdt_chuan"]
            chu_so = re.sub(r"\D", "", text)
            if kq["sdt_chuan"][-9:] not in chu_so:
                loi.append({"truong": "sdt", "ly_do": "không thấy số này trong hội thoại"})
                note("chặn: sđt model trả không có trong hội thoại")

    # Bước 6 · địa chỉ (chỉ gọi công cụ khi đủ tham số)
    tinh = truong["tinh_thanh"]
    if tinh and kieu_cu and truong["quan_huyen_cu"]:
        cu = ", ".join(t for t in (truong["phuong_xa_cu"], truong["quan_huyen_cu"]) if t)
        kq = convert_old_address(tinh, truong["quan_huyen_cu"], truong["phuong_xa_cu"] or "")
        moi = kq.get("phuong_moi") or []
        chon = None
        if kq.get("ket_qua") == "mot" and moi:
            chon = moi[0]
        elif kq.get("ket_qua") == "nhieu" and moi:
            # phường cũ bị tách: chỉ nhận phường khách đã chọn và có trong danh sách
            if truong["phuong_xa"]:
                tra = lookup_address(kq["tinh_moi"], truong["phuong_xa"])
                if tra.get("ok") and tra["khop"] in moi:
                    chon = tra["khop"]
            if not chon:
                goi_y = list(moi)
                loi.append({"truong": "dia_chi", "ly_do": "phường cũ bị tách, chờ khách chọn phường"})
        else:
            loi.append({"truong": "dia_chi", "ly_do": "không tìm thấy %s trong bảng chuyển đổi" % cu})
        if chon:
            quy_doi = {"tu": "%s, %s" % (cu, chuan_hoa_tinh(tinh)), "khoan": kq["khoan"],
                       "khach_chon": kq["ket_qua"] == "nhieu"}
            truong["phuong_xa"], truong["tinh_thanh"] = chon, kq["tinh_moi"]
    elif tinh and not kieu_cu and truong["phuong_xa"]:
        kq = lookup_address(tinh, truong["phuong_xa"])
        if kq.get("ok"):
            truong["phuong_xa"], truong["tinh_thanh"] = kq["khop"], kq["tinh"]
        else:
            goi_y = (kq.get("goi_y") or [])[:3]
            loi.append({"truong": "dia_chi", "ly_do": kq.get("ly_do") or "không tìm thấy phường/xã"})
    return truong, loi, goi_y, quy_doi


# ---------- tin nhắn ----------

def _tin_hoi_lai(loi, goi_y, truong):
    phan, da = [], set()
    for l in loi:
        k = l["truong"]
        if k == "dia_chi":
            continue
        if k in da:
            continue
        da.add(k)
        cau = TEN_TRUONG.get(k, k)
        if k == "sdt" and l["ly_do"] != "thiếu":
            cau += " (số anh/chị gửi chưa đúng, nhờ anh/chị gửi lại giúp em)"
        if k == "so_luong" and l["ly_do"] != "thiếu":
            cau += " (từ 1 trở lên)"
        phan.append(cau)
    for l in loi:
        if l["truong"] == "dia_chi":
            if goi_y:
                cu = truong.get("phuong_xa_cu")
                dau = "địa chỉ %s, %s nay thuộc" % (cu, truong.get("quan_huyen_cu")) if cu else "phường/xã nhận hàng là"
                phan.append("%s phường nào trong các phường sau ạ: %s" % (dau, ", ".join(goi_y)))
            else:
                phan.append("phường/xã nhận hàng (shop chưa tra được địa chỉ anh/chị gửi)")
            break
    return "Dạ shop cần thêm " + "; ".join(phan) + " ạ."


def _cho_chu_shop_hoi_lai(truong, loi):
    co = [NHAN_NGAN[k] for k in ("ten_nguoi_nhan", "sdt", "san_pham") if truong.get(k)
          and k not in {l["truong"] for l in loi}]
    thieu = [l["ly_do"] if l["ly_do"].startswith("phường cũ bị tách")
             else "%s %s" % (NHAN_NGAN.get(l["truong"], l["truong"]), l["ly_do"]) for l in loi]
    dau = ("đã có " + ", ".join(co) + " · ") if co else ""
    return "Cho chủ shop: " + dau + " · ".join(thieu) + " · chưa tạo đơn nháp"


def _dong_phuong(truong, quy_doi):
    if not quy_doi:
        return truong["phuong_xa"]
    return "%s (quy đổi từ %s theo khoản %s Nghị quyết 1685/NQ-UBTVQH15%s)" % (
        truong["phuong_xa"], quy_doi["tu"], ", ".join(str(k) for k in quy_doi["khoan"]),
        "; khách chọn" if quy_doi["khach_chon"] else "")


# ---------- luồng chính ----------

def xu_ly(text: str, ma_hoi_thoai=None) -> dict:
    kq = {"quyet_dinh": "HOI_LAI", "truong": {}, "loi": [], "goi_y_phuong": [], "tin_gui_khach": "",
          "cho_chu_shop": "", "ma_don": None, "ma_van_don": None}

    # Bước 1 · model đọc hội thoại
    reply = call_model(SYSTEM, text)
    info = doc_json(reply.get("text"))
    if info is None:
        note("model không trả JSON đọc được → hỏi lại cả thông tin nhận hàng")
        kq["loi"] = [{"truong": "tat_ca", "ly_do": "model không trả JSON đọc được"}]
        kq["tin_gui_khach"] = ("Dạ anh/chị cho shop xin tên người nhận, số điện thoại, địa chỉ nhận hàng "
                               "(số nhà, đường, phường/xã, tỉnh/thành), sản phẩm và số lượng ạ.")
        kq["cho_chu_shop"] = "Cho chủ shop: chưa đọc được thông tin nhận hàng · chưa tạo đơn nháp"
        return kq

    # Bước 2 (1.3 (d) bước 2) · yêu cầu ngoài phạm vi
    if _co(info.get("yeu_cau_ngoai_pham_vi")):
        note("từ chối: yêu cầu ngoài phạm vi")
        kq["quyet_dinh"] = "TU_CHOI"
        kq["tin_gui_khach"] = ("Dạ shop chỉ lên đơn khi đủ thông tin nhận hàng của chính đơn này, và không chia sẻ "
                               "thông tin của khách khác ạ. Anh/chị gửi giúp em tên, số điện thoại, địa chỉ người "
                               "nhận là shop lên đơn ngay ạ.")
        kq["cho_chu_shop"] = "Cho chủ shop: khách yêu cầu ngoài phạm vi (%s) · chưa tạo đơn nháp" % \
            lam_sach_luot(info.get("yeu_cau_ngoai_pham_vi"))[:120]
        return kq

    # Bước 3–6 · kiểm, gom lỗi
    truong, loi, goi_y, quy_doi = _kiem(info, text)
    kq["truong"], kq["loi"], kq["goi_y_phuong"] = truong, loi, goi_y
    if loi:
        kq["tin_gui_khach"] = _tin_hoi_lai(loi, goi_y, truong)
        kq["cho_chu_shop"] = _cho_chu_shop_hoi_lai(truong, loi)
        return kq

    # Bước 7 · tạo đơn nháp
    truong["ma_hoi_thoai"] = ma_hoi_thoai
    don = create_draft_order(truong)
    kq.update(quyet_dinh="TAO_DON_NHAP", ma_don=don["ma_don"], ma_van_don=don["ma_van_don"])
    phuong = _dong_phuong(truong, quy_doi)
    kq["tin_gui_khach"] = ("Dạ shop đã lên đơn, anh/chị kiểm lại giúp em ạ: %s · %s · %s, %s, %s · %s × %s."
                           % (truong["ten_nguoi_nhan"], truong["sdt"], truong["dia_chi_chi_tiet"],
                              truong["phuong_xa"], truong["tinh_thanh"], truong["san_pham"], truong["so_luong"]))
    kq["cho_chu_shop"] = "\n".join([
        "Cho chủ shop:",
        "Người nhận: %s" % truong["ten_nguoi_nhan"],
        "SĐT: %s" % truong["sdt"],
        "Địa chỉ: %s" % truong["dia_chi_chi_tiet"],
        "Phường/xã: %s" % phuong,
        "Tỉnh/thành: %s" % truong["tinh_thanh"],
        "Sản phẩm: %s × %s" % (truong["san_pham"], truong["so_luong"]),
        "Mã đơn: %s · Vận đơn: %s" % (don["ma_don"], don["ma_van_don"]),
    ])
    return kq


NHAN_QUYET_DINH = {"TAO_DON_NHAP": "TẠO ĐƠN NHÁP", "HOI_LAI": "HỎI LẠI", "TU_CHOI": "TỪ CHỐI"}


def answer(text: str) -> dict:
    kq = xu_ly(text)
    return {"output": "QUYẾT ĐỊNH: %s\nTin gửi khách: %s\n---\n%s"
            % (NHAN_QUYET_DINH[kq["quyet_dinh"]], kq["tin_gui_khach"], kq["cho_chu_shop"])}
