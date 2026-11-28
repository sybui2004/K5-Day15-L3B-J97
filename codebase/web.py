"""Luồng D + B · màn hình duyệt (task P2, docs/cp2-ke-hoach.md).

Chạy: python run.py  → mở http://127.0.0.1:8000 (chỉ máy này; bản dòng lệnh dự phòng: python codebase/app.py).

- Hộp thư: data/hop-thu-mau.jsonl qua inbox.xu_ly_hop_thu (P1), mỗi hội thoại một dòng trạng thái.
- Đơn nháp: chủ shop sửa trường nào thì code kiểm lại (validate_phone / lookup_address); sai thì khoá Duyệt.
  Duyệt chỉ đổi trạng thái thành da_duyet: KHÔNG gọi GHN, KHÔNG gửi tin.
- Luồng B: câu khách trả lời được ghép `| Shop: <tin gửi khách> | Khách: <trả lời>` (qua lam_sach_luot)
  rồi chạy lại agent.xu_ly trên cả hội thoại.
- Hội thoại mới: chủ shop / người demo gõ hội thoại trên màn hình (POST /api/moi), AI chạy ngay, mã HT-M01…
- Mỗi lần chạy AI giữ trace (bước model / công cụ, token, thời gian, chi phí theo giá ở cost/personas.yaml).
- Nhật ký duyệt và lần chạy: kho.py — Postgres khi có DATABASE_URL, không thì data/*.jsonl (không commit).

Giao diện: codebase/static/ (index.html, app.css, app.js, fonts/), dữ liệu khách chỉ đưa vào DOM bằng textContent / value.
Chỉ thư viện chuẩn (Postgres là tuỳ chọn, cần psycopg). Một luồng xử lý (tracing dùng biến toàn cục).
"""
import copy
import json
import os
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tracing  # noqa: E402
from agent import lam_sach_luot, xu_ly, _so_luong  # noqa: E402
from inbox import doc_hop_thu, xu_ly_hop_thu, THU_TU, _dung_text  # noqa: E402
from kho import KhoFile, LoiKho, mo_kho  # noqa: E402
from tools import validate_phone, lookup_address, create_draft_order, _bang, HCM  # noqa: E402

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOP_THU_THEM = os.path.join(GOC, "data", "hop-thu-them.jsonl")  # lô "Nhận tin mới" của chế độ NAP_NEN=1
NHAT_KY = os.path.join(GOC, "data", "nhat-ky-duyet.jsonl")
TINH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")  # giao diện: index.html, app.css, app.js, fonts/
LOAI_TEP = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
            ".js": "text/javascript; charset=utf-8", ".woff2": "font/woff2"}
PERSONAS = os.path.join(GOC, "cost", "personas.yaml")
MOI_TOI_DA_LUOT, MOI_TOI_DA_KY_TU = 30, 2000  # hội thoại gõ trên màn hình
# Giới hạn byte thân POST. /api/moi phải chứa được đầu vào hợp lệ lớn nhất: mỗi ký tự (code point) tối đa
# 12 byte JSON (cặp surrogate \uXXXX\uXXXX), mỗi lượt thêm khung {"vai":..,"tin":..}; ~0,7 MB.
GIOI_HAN_POST = 65536
GIOI_HAN_POST_MOI = MOI_TOI_DA_LUOT * (MOI_TOI_DA_KY_TU * 12 + 256) + 4096
HOST, PORT = "127.0.0.1", 8000
SUA_DUOC = ["ten_nguoi_nhan", "sdt", "dia_chi_chi_tiet", "phuong_xa", "san_pham", "so_luong"]
BAT_BUOC_CHU = ["ten_nguoi_nhan", "dia_chi_chi_tiet", "san_pham"]
TRANG_THAI = {"TAO_DON_NHAP": "cho_duyet", "HOI_LAI": "cho_khach", "TU_CHOI": "tu_choi"}
DA_XONG = ("da_duyet", "da_huy")


class LoiChayAI(Exception):
    """`ham` trong _co_trace ném lỗi. Giữ trace đo được tới lúc lỗi (token, bước) để vẫn ghi nhật ký."""

    def __init__(self, goc, trace):
        super().__init__("%s: %s" % (type(goc).__name__, goc))
        self.goc, self.trace = goc, trace


class LoiThaoTac(Exception):
    """Thao tác không làm được (sai trạng thái, sửa sai, model lỗi). `chi_tiet` gửi kèm cho màn hình."""

    def __init__(self, thong_bao, chi_tiet=None):
        super().__init__(thong_bao)
        self.chi_tiet = chi_tiet


# ---------- hàm kiểm khi sửa (test ở tests/test_web.py) ----------

def kiem_khi_sua(goc: dict, sua: dict) -> dict:
    """Áp các trường chủ shop sửa lên đơn nháp `goc` rồi kiểm lại.
    Trả {"truong": đơn sau khi sửa (đã chuẩn hoá chỗ hợp lệ), "loi": {trường: lý do}, "goi_y": {trường: [..]},
    "duoc_duyet": bool, "truong_da_sua": [trường có giá trị khác đơn gốc]}. Chỉ nhận trường trong SUA_DUOC."""
    truong = {k: goc.get(k) for k in SUA_DUOC + ["tinh_thanh"]}
    for k, v in (sua or {}).items():
        if k in SUA_DUOC:
            truong[k] = v
    loi, goi_y = {}, {}
    for k in BAT_BUOC_CHU:
        v = " ".join(str(truong[k] or "").split())
        truong[k] = v
        if not v:
            loi[k] = "không được để trống"
    kq = validate_phone(truong["sdt"])
    if kq["ok"]:
        truong["sdt"] = kq["sdt_chuan"]
    else:
        loi["sdt"] = kq["ly_do"]
    if not str(truong["phuong_xa"] or "").strip():
        loi["phuong_xa"] = "không được để trống"
    else:
        kq = lookup_address(truong["tinh_thanh"] or HCM, truong["phuong_xa"])
        if kq["ok"]:
            truong["phuong_xa"], truong["tinh_thanh"] = kq["khop"], kq["tinh"]
        else:
            loi["phuong_xa"], goi_y["phuong_xa"] = kq["ly_do"], kq["goi_y"]
    sl, ly_do = _so_luong(truong["so_luong"] if not isinstance(truong["so_luong"], str)
                          else truong["so_luong"].strip())
    if ly_do:
        loi["so_luong"] = ly_do
    else:
        truong["so_luong"] = sl
    da_sua = [k for k in SUA_DUOC if k in (sua or {}) and truong[k] != goc.get(k)]
    return {"truong": truong, "loi": loi, "goi_y": goi_y, "duoc_duyet": not loi, "truong_da_sua": da_sua}


def ghep_tra_loi(text: str, tin_gui_khach: str, tra_loi: str) -> str:
    """Luồng B: nối tin shop đã gửi và câu khách trả lời vào cuối hội thoại, vẫn trên một dòng (1.3 (a)).
    Tin gửi khách rỗng (lỗi hệ thống, shop tự nhắn) thì chỉ nối câu khách."""
    tra_loi = lam_sach_luot(tra_loi or "")
    if not tra_loi:
        raise ValueError("câu khách trả lời đang trống")
    phan = [text]
    tin = lam_sach_luot(tin_gui_khach or "")
    if tin:
        phan.append("Shop: " + tin)
    phan.append("Khách: " + tra_loi)
    return " | ".join(phan)


def _bang_gia():
    """Giá model (USD / 1 triệu token) và tỉ giá từ cost/personas.yaml. Đọc lỗi thì coi như chưa có giá."""
    try:
        sys.path.insert(0, os.path.join(GOC, "eval"))
        from run_eval import load_yaml
        cfg = load_yaml(PERSONAS) or {}
    except Exception:
        return [], None
    gia = [g for g in (cfg.get("prices") or []) if isinstance(g, dict) and g.get("model")]
    rate = (cfg.get("usd_to_vnd") or {}).get("rate") if isinstance(cfg.get("usd_to_vnd"), dict) else None
    return gia, rate if isinstance(rate, (int, float)) and not isinstance(rate, bool) else None


def chi_phi(model: str, tokens_in: int, tokens_out: int, bang_gia: list):
    """USD cho một lần chạy theo bảng giá (USD / 1 triệu token). Không có giá cho model này thì trả None.
    Tên model API có thể kèm hậu tố ngày (claude-sonnet-5-5-20261101) nên khớp cả theo tiền tố."""
    if not model:
        return None
    for g in sorted(bang_gia, key=lambda g: -len(str(g["model"]))):
        ten = str(g["model"])
        if model == ten or model.startswith(ten + "-"):
            vao, ra = g.get("input"), g.get("output")
            if not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in (vao, ra)):
                return None
            return (tokens_in * vao + tokens_out * ra) / 1_000_000
    return None


def chi_phi_su_kien(su_kien, bang_gia: list):
    """USD cho một lần chạy, tính trên từng lần gọi model (kind == "model") theo đúng model của lần đó rồi cộng.
    Một lần chạy có thể có hai model (lớp chặn NeMo và bước đọc đơn, hoặc API chuyển sang model dự phòng).
    Có lần gọi nào chưa định giá được, hoặc không có lần gọi model nào, thì trả None (chưa đủ giá)."""
    goi = [e for e in su_kien if e.get("kind") == "model"]
    if not goi:
        return None
    tong = 0.0
    for e in goi:
        c = chi_phi(e.get("model") or "", e.get("tokens_in") or 0, e.get("tokens_out") or 0, bang_gia)
        if c is None:
            return None
        tong += c
    return tong


def _buoc(e):
    """Một sự kiện trace → một bước cho màn hình. Bỏ input của model (system prompt dài, không giúp người xem)."""
    b = {"loai": e.get("kind"), "ten": e.get("name") or "", "t": e.get("t")}
    giu = ("latency_s", "model", "tokens_in", "tokens_out", "output", "error") if e.get("kind") == "model" else \
        ("latency_s", "input", "output", "error", "text")
    for k in giu:
        if e.get(k) not in (None, ""):
            b[k] = e[k]
    return b


def _co_trace(nhan, ham, *args, nguon="hop_thu", bang_gia=()):
    """Chạy `ham` trong một case trace (như app.py), in tóm tắt ra màn hình.
    Trả (kết quả, trace) với trace = {nguon, buoc, model_calls, tool_calls, tokens_in, tokens_out, model,
    thoi_gian_s, chi_phi_usd (None nếu chưa có giá), loi}. `ham` ném lỗi thì ném LoiChayAI kèm trace."""
    tracing.begin(nhan)
    t0 = time.perf_counter()
    loi_ham = None
    try:
        kq = ham(*args)
    except Exception as e:  # model lỗi, mất mạng…: vẫn giữ trace đo được
        loi_ham, kq = e, None
    finally:
        s, su_kien = tracing.end()
    loi = list(s["errors"])
    if loi_ham is not None and not loi:
        loi.append("%s: %s" % (type(loi_ham).__name__, loi_ham))
    print("   [%s] model %d lần · công cụ %d lần · token vào %d / ra %d%s"
          % (nhan, s["model_calls"], s["tool_calls"], s["tokens_in"], s["tokens_out"],
             " · lỗi: %s" % "; ".join(loi) if loi else ""))
    model = s["models"][0] if s["models"] else ""
    trace = {"nguon": nguon, "buoc": [_buoc(e) for e in su_kien], "model_calls": s["model_calls"],
             "tool_calls": s["tool_calls"], "tokens_in": s["tokens_in"], "tokens_out": s["tokens_out"],
             "model": model, "thoi_gian_s": round(time.perf_counter() - t0, 3),
             "chi_phi_usd": chi_phi_su_kien(su_kien, list(bang_gia)), "loi": loi}
    if loi_ham is not None:
        raise LoiChayAI(loi_ham, trace) from loi_ham
    return kq, trace


def kiem_hoi_thoai_moi(luot, ma_khach=None) -> str:
    """Kiểm hội thoại gõ trên màn hình rồi ghép như hộp thư (inbox._dung_text). Sai thì ném ValueError."""
    if not isinstance(luot, list) or not luot:
        raise ValueError("cần ít nhất một lượt tin nhắn")
    if len(luot) > MOI_TOI_DA_LUOT:
        raise ValueError("tối đa %d lượt tin nhắn" % MOI_TOI_DA_LUOT)
    sach = []
    for i, l in enumerate(luot, 1):
        if not isinstance(l, dict) or not isinstance(l.get("tin"), str):
            raise ValueError("lượt %d thiếu nội dung tin" % i)
        if len(l["tin"]) > MOI_TOI_DA_KY_TU:
            raise ValueError("lượt %d dài quá %d ký tự" % (i, MOI_TOI_DA_KY_TU))
        if not lam_sach_luot(l["tin"]):
            raise ValueError("lượt %d đang trống" % i)
        sach.append({"vai": l.get("vai"), "tin": l["tin"]})
    if not any(l["vai"] == "khach" for l in sach):
        raise ValueError("cần ít nhất một tin của khách")
    ma_khach = (ma_khach or "").strip() or None
    if ma_khach and not re.fullmatch(r"KH-[0-9]{1,9}", ma_khach):
        raise ValueError("mã khách phải dạng KH-<số>, vd KH-201")
    return _dung_text({"ma_khach": ma_khach, "luot": sach})


# ---------- trạng thái màn hình ----------

class ManHinh:
    """Giữ hộp thư trong bộ nhớ. Mỗi phiên: ma_hoi_thoai, ma_khach, text, loi_doc, kq (kết quả xu_ly),
    trang_thai (cho_duyet / cho_khach / tu_choi / da_duyet / da_huy), so_luot_hoi_lai, ma_don, ma_van_don,
    nguon (hop_thu / moi), trace (lần chạy AI gần nhất, xem _co_trace)."""

    def __init__(self, nhat_ky=NHAT_KY, kho=None):
        self.kho = kho or KhoFile(nhat_ky)
        self._phien = {}
        self._khoa = threading.Lock()
        # tracing dùng biến toàn cục cho lần chạy hiện tại: mọi lần chạy AI (kể cả luồng nền) đi qua khoá này,
        # lần lượt từng lần. Thứ tự khoá: _khoa rồi mới _khoa_ai; luồng nền không giữ _khoa khi chờ _khoa_ai.
        self._khoa_ai = threading.Lock()
        self.cho_nap_nen = False  # NAP_NEN=1: bật nút "Nhận tin mới" và /api/nhan-them
        self._so_moi = 0
        self._bang_gia, self.ty_gia = _bang_gia()
        self._tong = {"lan_chay": 0, "model_calls": 0, "tokens_in": 0, "tokens_out": 0, "chi_phi_usd": 0.0,
                      "lan_chua_co_gia": 0, "loi_kho": None}

    def _chay(self, ma, nguon, ham, *args):
        with self._khoa_ai:
            return _co_trace("web:" + str(ma), ham, *args, nguon=nguon, bang_gia=self._bang_gia)

    def _luu_lan_chay(self, ma, quyet_dinh, trace):
        """Cộng tổng phiên demo và ghi kho ngay khi một lần chạy AI kết thúc (cả lần lỗi: quyet_dinh None).
        Kho lỗi chỉ ghi lại lỗi, không chặn demo. Gọi khi đang giữ self._khoa (hoặc chưa mở server)."""
        t = self._tong
        t["lan_chay"] += 1
        t["model_calls"] += trace["model_calls"]
        t["tokens_in"] += trace["tokens_in"]
        t["tokens_out"] += trace["tokens_out"]
        if trace["chi_phi_usd"] is None:
            t["lan_chua_co_gia"] += trace["model_calls"] > 0
        else:
            t["chi_phi_usd"] += trace["chi_phi_usd"]
        try:
            self.kho.ghi_lan_chay({"ma_hoi_thoai": ma, "nguon": trace["nguon"], "quyet_dinh": quyet_dinh,
                                   "trace": trace, "luc": time.strftime("%Y-%m-%dT%H:%M:%S")})
        except OSError as e:
            t["loi_kho"] = str(e)
            print("   [kho] chưa ghi được lần chạy %s: %s" % (ma, e))

    def _chay_va_luu(self, ma, nguon, ham, *args):
        """Chạy AI rồi ghi lần chạy ngay. Lỗi thì ghi trace lỗi rồi ném LoiChayAI (trạng thái hội thoại chưa đổi)."""
        try:
            kq, trace = self._chay(ma, nguon, ham, *args)
        except LoiChayAI as e:
            self._luu_lan_chay(ma, None, e.trace)
            raise
        return kq, trace

    def _phien_moi(self, ma, h, kq, nguon):
        kq = {k: v for k, v in kq.items() if k != "ma_hoi_thoai"}
        return {"ma_hoi_thoai": ma, "ma_khach": h.get("ma_khach"), "text": h.get("text", ""),
                "loi_doc": h.get("loi_doc"), "kq": kq, "trang_thai": TRANG_THAI.get(kq["quyet_dinh"], "cho_khach"),
                "so_luot_hoi_lai": 0, "ma_don": kq.get("ma_don"), "ma_van_don": kq.get("ma_van_don"),
                "nguon": nguon, "trace": None, "phien_ban": 1}

    @staticmethod
    def _phien_cho(ma, h, nguon):
        """Hội thoại vừa đến, AI chưa xử lý xong (chế độ nạp nền)."""
        kq = {"quyet_dinh": None, "truong": {}, "loi": [], "goi_y_phuong": [], "tin_gui_khach": "", "cho_chu_shop": "",
              "ma_don": None, "ma_van_don": None}
        return {"ma_hoi_thoai": ma, "ma_khach": h.get("ma_khach"), "text": h.get("text", ""), "loi_doc": h.get("loi_doc"),
                "kq": kq, "trang_thai": "dang_xu_ly", "so_luot_hoi_lai": 0, "ma_don": None, "ma_van_don": None,
                "nguon": nguon, "trace": None, "phien_ban": 0}

    def nap_nen(self, hoi_thoai: list, nguon="hop_thu"):
        """Chế độ tin đến hàng loạt: đưa cả lô lên đầu hộp thư ngay (trạng thái dang_xu_ly), rồi AI xử lý từng
        hội thoại ở luồng nền theo thứ tự đến. Mã trùng (với hộp thư hoặc trong lô) được cấp mã riêng (HT-1*).
        Trả về luồng nền (test dùng join)."""
        with self._khoa:
            lo = []
            for h in hoi_thoai:
                ma = str(h.get("ma_hoi_thoai"))
                while ma in self._phien or any(ma == m for m, _ in lo):
                    ma += "*"
                lo.append((ma, dict(h, ma_hoi_thoai=ma)))
            self._phien = {**{ma: self._phien_cho(ma, h, nguon) for ma, h in lo}, **self._phien}
        luong = threading.Thread(target=self._xu_ly_nen, args=(lo, nguon), daemon=True, name="nap-nen")
        luong.start()
        return luong

    def _xu_ly_nen(self, lo, nguon):
        for ma, h in lo:
            try:
                [kq], trace = self._chay(ma, nguon, xu_ly_hop_thu, [h])  # giữ _khoa_ai, không giữ _khoa
                loi = None
            except LoiChayAI as e:
                kq, trace, loi = None, e.trace, e
            except Exception as e:  # noqa: BLE001 — luồng nền không được chết giữa lô
                kq, trace, loi = None, None, e
            with self._khoa:
                if trace is not None:
                    self._luu_lan_chay(ma, kq["quyet_dinh"] if kq else None, trace)
                if kq is not None:
                    p = dict(self._phien_moi(ma, h, kq, nguon), trace=trace)
                else:
                    p = self._phien_cho(ma, h, nguon)
                    p["kq"].update(quyet_dinh="HOI_LAI", loi=[{"truong": "tat_ca", "ly_do": "AI chưa xử lý được (%s), "
                                   "shop xử lý tay hoặc dán câu khách để chạy lại" % loi}],
                                   cho_chu_shop="Cho chủ shop: AI chưa xử lý được hội thoại này · chưa tạo đơn nháp")
                    p.update(trang_thai="cho_khach", trace=trace, phien_ban=1)
                self._phien[ma] = p

    def tai(self, hoi_thoai: list):
        """Chạy AI cho cả hộp thư. Nhật ký ghi theo đúng thứ tự chạy; chỉ danh sách hiển thị được sắp lại.
        Mã trùng trong file được cấp mã riêng (HT-1, HT-1*) TRƯỚC khi chạy, dùng chung cho trace, nhật ký, hộp thư."""
        ra, da_cap = [], set()
        with self._khoa:
            for h in hoi_thoai:
                ma = str(h.get("ma_hoi_thoai"))
                while ma in da_cap:  # mã trùng trong file: giữ cả hai
                    ma += "*"
                da_cap.add(ma)
                h = dict(h, ma_hoi_thoai=ma)
                [kq], trace = self._chay_va_luu(ma, "hop_thu", xu_ly_hop_thu, [h])
                self._luu_lan_chay(ma, kq["quyet_dinh"], trace)  # ghi ngay khi chạy xong
                ra.append((ma, h, kq, trace))
            ra.sort(key=lambda x: THU_TU.get(x[2]["quyet_dinh"], THU_TU["HOI_LAI"]))  # chỉ thứ tự hiển thị
            self._phien = {ma: dict(self._phien_moi(ma, h, kq, "hop_thu"), trace=trace) for ma, h, kq, trace in ra}

    def tao_moi(self, luot, ma_khach=None):
        """Hội thoại gõ trên màn hình (vd câu thử lạ giám khảo đưa lúc demo): kiểm, chạy AI, đưa lên đầu hộp thư."""
        try:
            text = kiem_hoi_thoai_moi(luot, ma_khach)
        except ValueError as e:
            raise LoiThaoTac(str(e))
        with self._khoa:
            so = self._so_moi + 1
            while "HT-M%02d" % so in self._phien:
                so += 1
            ma = "HT-M%02d" % so
            try:
                kq, trace = self._chay_va_luu(ma, "moi", xu_ly, text, ma)
            except LoiChayAI as e:  # model lỗi, mất mạng…: trace lỗi đã ghi, không thêm hội thoại
                raise LoiThaoTac("chưa chạy được AI cho hội thoại mới (%s), thử lại" % e)
            self._luu_lan_chay(ma, kq["quyet_dinh"], trace)
            self._so_moi = so
            p = self._phien_moi(ma, {"ma_khach": (ma_khach or "").strip() or None, "text": text}, kq, "moi")
            p["trace"] = trace
            self._phien = {ma: p, **self._phien}
            return copy.deepcopy(p)

    def tong(self):
        """Tổng phiên demo (từ lúc mở màn hình): số lần chạy, token, chi phí USD (+ VND nếu có tỉ giá)."""
        with self._khoa:
            t = dict(self._tong)
            t["dang_xu_ly"] = sum(p["trang_thai"] == "dang_xu_ly" for p in self._phien.values())
        t["nap_nen"] = self.cho_nap_nen
        t["chi_phi_vnd"] = round(t["chi_phi_usd"] * self.ty_gia) if self.ty_gia else None
        t["kho"] = self.kho.ten
        return t

    def nhat_ky(self, gioi_han=100):
        try:
            return self.kho.doc_nhat_ky(gioi_han)
        except OSError as e:
            raise LoiThaoTac("chưa đọc được nhật ký (%s)" % e)

    def danh_sach(self):
        with self._khoa:
            return copy.deepcopy(list(self._phien.values()))

    def lay(self, ma):
        with self._khoa:
            return copy.deepcopy(self._lay(ma))

    def _lay(self, ma):
        if ma not in self._phien:
            raise LoiThaoTac("không có hội thoại %s" % ma)
        return self._phien[ma]

    @staticmethod
    def _chua_xu_ly_xong(p):
        if p["trang_thai"] == "dang_xu_ly":
            raise LoiThaoTac("hội thoại %s đang được AI xử lý, chờ vài giây" % p["ma_hoi_thoai"])

    @staticmethod
    def _dung_phien_ban(p, phien_ban):
        """Phiếu gửi kèm phiên bản cũ (AI vừa đọc lại hội thoại sau khi phiếu được mở) thì từ chối,
        để không áp trường của phiếu cũ lên đơn nháp mới. Không gửi phiên bản thì bỏ qua (gọi từ code)."""
        if phien_ban is not None and phien_ban != p["phien_ban"]:
            raise LoiThaoTac("hội thoại %s vừa được AI đọc lại, phiếu đang mở đã cũ — xem lại phiếu mới rồi duyệt"
                             % p["ma_hoi_thoai"])

    def kiem(self, ma, sua, phien_ban=None):
        with self._khoa:
            p = self._lay(ma)
            if p["trang_thai"] != "cho_duyet":
                raise LoiThaoTac("hội thoại %s không có đơn nháp chờ duyệt" % ma)
            self._dung_phien_ban(p, phien_ban)
            return kiem_khi_sua(p["kq"]["truong"], sua)

    def duyet(self, ma, sua, phien_ban=None):
        with self._khoa:
            p = self._lay(ma)
            if p["trang_thai"] != "cho_duyet":
                raise LoiThaoTac("hội thoại %s không có đơn nháp chờ duyệt" % ma)
            self._dung_phien_ban(p, phien_ban)
            k = kiem_khi_sua(p["kq"]["truong"], sua)
            if not k["duoc_duyet"]:
                raise LoiThaoTac("còn trường chưa qua kiểm, chưa duyệt được", k)
            don = create_draft_order(dict(k["truong"], ma_hoi_thoai=ma))  # chỉ tính mã nháp, không gọi GHN
            self._ghi(p, "da_duyet", k["truong_da_sua"])  # ghi nhật ký được rồi mới chốt trạng thái
            p.update(trang_thai="da_duyet", ma_don=don["ma_don"], ma_van_don=don["ma_van_don"],
                     truong_duyet=k["truong"], truong_da_sua=k["truong_da_sua"])
            return copy.deepcopy(p)

    def huy(self, ma):
        with self._khoa:
            p = self._lay(ma)
            self._chua_xu_ly_xong(p)
            if p["trang_thai"] in DA_XONG:
                raise LoiThaoTac("hội thoại %s đã %s" % (ma, "duyệt" if p["trang_thai"] == "da_duyet" else "huỷ"))
            self._ghi(p, "da_huy", [])  # ghi nhật ký được rồi mới chốt trạng thái
            p["trang_thai"] = "da_huy"
            return copy.deepcopy(p)

    def them_tra_loi(self, ma, tra_loi):
        """Luồng B: ghép câu khách trả lời rồi chạy lại xu_ly. Model lỗi thì giữ nguyên hội thoại để thử lại.
        - Đang HỎI LẠI: nối tin hỏi lại của shop + câu khách, tính một lượt hỏi lại.
        - Đang TỪ CHỐI: nối tin từ chối + câu khách, không tính là hỏi lại.
        - Đang có đơn nháp chờ duyệt: tin xác nhận chưa gửi khách, nên chỉ nối câu khách nhắn thêm, không tính."""
        with self._khoa:
            p = self._lay(ma)
            self._chua_xu_ly_xong(p)
            if p["trang_thai"] in DA_XONG:
                raise LoiThaoTac("hội thoại %s đã xong, không thêm trả lời được" % ma)
            if p["loi_doc"] or not p["text"]:
                raise LoiThaoTac("hội thoại %s không đọc được từ hộp thư, shop xử lý tay" % ma)
            tin = "" if p["trang_thai"] == "cho_duyet" else p["kq"]["tin_gui_khach"]
            hoi_lai = p["kq"]["quyet_dinh"] == "HOI_LAI" and bool(lam_sach_luot(tin or ""))
            try:
                text = ghep_tra_loi(p["text"], tin, tra_loi)
            except ValueError as e:
                raise LoiThaoTac(str(e))
            try:
                kq, trace = self._chay_va_luu(ma, "tra_loi", xu_ly, text, ma)
            except LoiChayAI as e:  # model lỗi, mất mạng…: trace lỗi đã ghi, hội thoại giữ nguyên để thử lại
                raise LoiThaoTac("chưa xử lý được câu trả lời (%s), thử lại sau" % e)
            self._luu_lan_chay(ma, kq["quyet_dinh"], trace)
            p.update(text=text, kq=kq, trang_thai=TRANG_THAI.get(kq["quyet_dinh"], "cho_khach"),
                     so_luot_hoi_lai=p["so_luot_hoi_lai"] + (1 if hoi_lai else 0), ma_don=kq.get("ma_don"),
                     ma_van_don=kq.get("ma_van_don"), trace=trace, phien_ban=p["phien_ban"] + 1)
            return copy.deepcopy(p)

    def _ghi(self, p, ket_qua, da_sua):
        """Ghi nhật ký; lỗi thì báo để chủ shop thử lại (trạng thái chưa đổi)."""
        try:
            self.kho.ghi_duyet({"ma_hoi_thoai": p["ma_hoi_thoai"], "quyet_dinh_ai": p["kq"]["quyet_dinh"],
                                       "truong_da_sua": da_sua, "so_luot_hoi_lai": p["so_luot_hoi_lai"],
                                       "ket_qua": ket_qua, "luc": time.strftime("%Y-%m-%dT%H:%M:%S")})
        except OSError as e:
            raise LoiThaoTac("chưa ghi được nhật ký duyệt (%s), đơn chưa đổi trạng thái — thử lại" % e)


# ---------- HTTP ----------

def host_hop_le(host) -> bool:
    """Chỉ nhận Host trỏ về máy này (chặn DNS rebinding)."""
    return host in ("%s:%d" % (HOST, PORT), "localhost:%d" % PORT)


def post_hop_le(headers) -> bool:
    """POST phải có header riêng + JSON: trang web lạ không gửi được khi không qua preflight CORS (chặn CSRF)."""
    return headers.get("X-Man-Hinh-Duyet") == "1" and \
        (headers.get("Content-Type") or "").split(";")[0].strip() == "application/json"


def tep_tinh(duong: str):
    """Đường dẫn GET → (nội dung, loại) của một file trong codebase/static/, hoặc None.
    Chỉ nhận tên gồm chữ, số, '-', '_', '.' và tối đa một thư mục con; không cho '..' hay ra ngoài static/."""
    duong = duong.split("?", 1)[0].split("#", 1)[0]
    if duong == "/":
        duong = "/index.html"
    if not re.fullmatch(r"/(?:[a-z0-9_-]+/)?[a-z0-9_-]+(?:\.[a-z0-9_-]+)*\.[a-z0-9]+", duong) or ".." in duong:
        return None
    loai = LOAI_TEP.get(os.path.splitext(duong)[1])
    tep = os.path.realpath(os.path.join(TINH, duong.lstrip("/")))
    if not loai or not tep.startswith(os.path.realpath(TINH) + os.sep) or not os.path.isfile(tep):
        return None
    with open(tep, "rb") as f:
        return f.read(), loai


def _phuong_moi():
    return sorted({r["phuong_xa_moi"] for r in _bang()})


class XuLyYeuCau(BaseHTTPRequestHandler):
    man_hinh = None  # gán trước khi chạy server

    def log_message(self, fmt, *args):  # gọn màn hình console
        pass

    def _gui(self, code, body, kieu="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", kieu)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy",
                         "default-src 'none'; script-src 'self'; style-src 'self'; font-src 'self'; connect-src 'self'; "
                         "base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if not host_hop_le(self.headers.get("Host")):
            return self._gui(403, {"loi": "Host không hợp lệ"})
        if self.path == "/api/hop-thu":
            return self._gui(200, {"phien": self.man_hinh.danh_sach(), "phuong_moi": _phuong_moi(),
                                   "tong": self.man_hinh.tong()})
        if self.path == "/api/nhat-ky":
            try:
                return self._gui(200, self.man_hinh.nhat_ky())
            except LoiThaoTac as e:
                return self._gui(503, {"loi": str(e)})
        tep = tep_tinh(self.path)
        if tep:
            return self._gui(200, *tep)
        return self._gui(404, {"loi": "không có"})

    def do_POST(self):
        if not host_hop_le(self.headers.get("Host")) or not post_hop_le(self.headers):
            return self._gui(403, {"loi": "yêu cầu không hợp lệ"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n < 0 or n > (GIOI_HAN_POST_MOI if self.path == "/api/moi" else GIOI_HAN_POST):
                return self._gui(413, {"loi": "dữ liệu quá lớn"})
            body = json.loads(self.rfile.read(n) or b"{}")
            if not isinstance(body, dict):
                raise ValueError("cần object JSON")
        except ValueError as e:
            return self._gui(400, {"loi": "JSON hỏng: %s" % e})
        ma, sua = str(body.get("ma") or ""), body.get("sua") or {}
        if not isinstance(sua, dict):
            return self._gui(400, {"loi": "sua phải là object"})
        pb = body.get("phien_ban")
        if pb is not None and (not isinstance(pb, int) or isinstance(pb, bool)):
            return self._gui(400, {"loi": "phien_ban phải là số nguyên"})
        mh = self.man_hinh
        try:
            if self.path == "/api/kiem":
                return self._gui(200, mh.kiem(ma, sua, pb))
            if self.path == "/api/duyet":
                return self._gui(200, mh.duyet(ma, sua, pb))
            if self.path == "/api/huy":
                return self._gui(200, mh.huy(ma))
            if self.path == "/api/tra-loi":
                return self._gui(200, mh.them_tra_loi(ma, str(body.get("tra_loi") or "")))
            if self.path == "/api/nhan-them":
                if not mh.cho_nap_nen:
                    return self._gui(404, {"loi": "chỉ có khi chạy với NAP_NEN=1"})
                lo = doc_hop_thu(HOP_THU_THEM)
                mh.nap_nen(lo)
                return self._gui(200, {"so": len(lo)})
            if self.path == "/api/moi":
                ma_khach = body.get("ma_khach")
                return self._gui(200, mh.tao_moi(body.get("luot"), ma_khach if isinstance(ma_khach, str) else None))
        except LoiThaoTac as e:
            return self._gui(400, {"loi": str(e), "chi_tiet": e.chi_tiet})
        return self._gui(404, {"loi": "không có"})


def _mo_kho():
    """Có DATABASE_URL mà Postgres lỗi thì báo rõ rồi ghi file, để demo vẫn chạy."""
    try:
        return mo_kho(NHAT_KY)
    except LoiKho as e:
        print("Không mở được Postgres (%s) → ghi nhật ký vào data/*.jsonl" % e)
        return KhoFile(NHAT_KY)


class MayChu(HTTPServer):
    # Windows: SO_REUSEADDR cho tiến trình khác mở chung cổng đang dùng → tắt; nơi khác giữ mặc định
    allow_reuse_address = os.name != "nt"


def main() -> int:
    # mở cổng trước: cổng bận thì dừng ngay, không gọi model cho cả hộp thư
    try:
        server = MayChu((HOST, PORT), XuLyYeuCau)
    except OSError as e:
        print("Không mở được %s:%d (%s). Cổng đang bận? Tắt chương trình đang dùng cổng rồi chạy lại." % (HOST, PORT, e))
        return 1
    nap_nen = os.environ.get("NAP_NEN", "").strip() == "1"
    try:
        hop_thu = doc_hop_thu()
        mh = ManHinh(kho=_mo_kho())
        print("Nhật ký duyệt và lần chạy AI lưu ở: %s" % mh.kho.ten)
        if nap_nen:  # tin đến hàng loạt: mở trang ngay, AI xử lý hộp thư ở luồng nền
            mh.cho_nap_nen = True
            XuLyYeuCau.man_hinh = mh
            print("Chế độ tin đến hàng loạt (NAP_NEN=1): AI xử lý %d hội thoại ở nền, trang tự cập nhật" % len(hop_thu))
            mh.nap_nen(hop_thu)
        else:
            print("Màn hình duyệt — đang xử lý %d hội thoại trong hộp thư mẫu..." % len(hop_thu))
            mh.tai(hop_thu)
            XuLyYeuCau.man_hinh = mh
    except BaseException:
        server.server_close()
        raise
    print("Mở trình duyệt: http://%s:%d   (chỉ máy này) · Thoát: Ctrl+C" % (HOST, PORT))
    print("Bản dòng lệnh dự phòng: python codebase/app.py")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
