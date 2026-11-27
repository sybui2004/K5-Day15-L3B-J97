"""Luồng D + B · màn hình duyệt (task P2, docs/cp2-ke-hoach.md).

Chạy: python run.py  → mở http://127.0.0.1:8000 (chỉ máy này; bản dòng lệnh dự phòng: python codebase/app.py).

- Hộp thư: data/hop-thu-mau.jsonl qua inbox.xu_ly_hop_thu (P1), mỗi hội thoại một dòng trạng thái.
- Đơn nháp: chủ shop sửa trường nào thì code kiểm lại (validate_phone / lookup_address); sai thì khoá Duyệt.
  Duyệt chỉ đổi trạng thái thành da_duyet: KHÔNG gọi GHN, KHÔNG gửi tin.
- Luồng B: câu khách trả lời được ghép `| Shop: <tin gửi khách> | Khách: <trả lời>` (qua lam_sach_luot)
  rồi chạy lại agent.xu_ly trên cả hội thoại.
- Nhật ký duyệt: data/nhat-ky-duyet.jsonl (không commit, xem .gitignore).

Chỉ thư viện chuẩn. Một luồng xử lý (tracing dùng biến toàn cục).
"""
import copy
import json
import os
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
from inbox import doc_hop_thu, xu_ly_hop_thu, THU_TU  # noqa: E402
from tools import validate_phone, lookup_address, create_draft_order, _bang, HCM  # noqa: E402

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NHAT_KY = os.path.join(GOC, "data", "nhat-ky-duyet.jsonl")
HOST, PORT = "127.0.0.1", 8000
SUA_DUOC = ["ten_nguoi_nhan", "sdt", "dia_chi_chi_tiet", "phuong_xa", "san_pham", "so_luong"]
BAT_BUOC_CHU = ["ten_nguoi_nhan", "dia_chi_chi_tiet", "san_pham"]
TRANG_THAI = {"TAO_DON_NHAP": "cho_duyet", "HOI_LAI": "cho_khach", "TU_CHOI": "tu_choi"}
DA_XONG = ("da_duyet", "da_huy")


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


def ghi_nhat_ky(path: str, dong: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(dong, ensure_ascii=False) + "\n")


def _co_trace(nhan, ham, *args):
    """Chạy `ham` trong một case trace (như app.py) và in tóm tắt số lần gọi model / token ra màn hình."""
    tracing.begin(nhan)
    try:
        return ham(*args)
    finally:
        s, _ = tracing.end()
        print("   [%s] model %d lần · công cụ %d lần · token vào %d / ra %d%s"
              % (nhan, s["model_calls"], s["tool_calls"], s["tokens_in"], s["tokens_out"],
                 " · lỗi: %s" % "; ".join(s["errors"]) if s["errors"] else ""))


# ---------- trạng thái màn hình ----------

class ManHinh:
    """Giữ hộp thư trong bộ nhớ. Mỗi phiên: ma_hoi_thoai, ma_khach, text, loi_doc, kq (kết quả xu_ly),
    trang_thai (cho_duyet / cho_khach / tu_choi / da_duyet / da_huy), so_luot_hoi_lai, ma_don, ma_van_don."""

    def __init__(self, nhat_ky=NHAT_KY):
        self.nhat_ky = nhat_ky
        self._phien = {}
        self._khoa = threading.Lock()

    def tai(self, hoi_thoai: list):
        ra = []
        for h in hoi_thoai:
            [kq] = _co_trace("web:" + str(h.get("ma_hoi_thoai")), xu_ly_hop_thu, [h])
            ra.append((h, kq))
        ra.sort(key=lambda x: THU_TU.get(x[1]["quyet_dinh"], THU_TU["HOI_LAI"]))
        with self._khoa:
            self._phien = {}
            for h, kq in ra:
                ma = str(kq["ma_hoi_thoai"])
                while ma in self._phien:  # mã trùng trong file: giữ cả hai
                    ma += "*"
                kq = {k: v for k, v in kq.items() if k != "ma_hoi_thoai"}
                self._phien[ma] = {"ma_hoi_thoai": ma, "ma_khach": h.get("ma_khach"), "text": h.get("text", ""),
                                   "loi_doc": h.get("loi_doc"), "kq": kq, "trang_thai": TRANG_THAI[kq["quyet_dinh"]],
                                   "so_luot_hoi_lai": 0, "ma_don": kq.get("ma_don"),
                                   "ma_van_don": kq.get("ma_van_don")}

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

    def kiem(self, ma, sua):
        with self._khoa:
            p = self._lay(ma)
            if p["trang_thai"] != "cho_duyet":
                raise LoiThaoTac("hội thoại %s không có đơn nháp chờ duyệt" % ma)
            return kiem_khi_sua(p["kq"]["truong"], sua)

    def duyet(self, ma, sua):
        with self._khoa:
            p = self._lay(ma)
            if p["trang_thai"] != "cho_duyet":
                raise LoiThaoTac("hội thoại %s không có đơn nháp chờ duyệt" % ma)
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
                kq = _co_trace("web:" + ma, xu_ly, text, ma)
            except Exception as e:  # model lỗi, mất mạng…
                raise LoiThaoTac("chưa xử lý được câu trả lời (%s: %s), thử lại sau" % (type(e).__name__, e))
            p.update(text=text, kq=kq, trang_thai=TRANG_THAI.get(kq["quyet_dinh"], "cho_khach"),
                     so_luot_hoi_lai=p["so_luot_hoi_lai"] + (1 if hoi_lai else 0), ma_don=kq.get("ma_don"),
                     ma_van_don=kq.get("ma_van_don"))
            return copy.deepcopy(p)

    def _ghi(self, p, ket_qua, da_sua):
        """Ghi nhật ký; lỗi thì báo để chủ shop thử lại (trạng thái chưa đổi)."""
        try:
            ghi_nhat_ky(self.nhat_ky, {"ma_hoi_thoai": p["ma_hoi_thoai"], "quyet_dinh_ai": p["kq"]["quyet_dinh"],
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
                         "default-src 'none'; script-src 'self'; style-src 'unsafe-inline'; connect-src 'self'; "
                         "base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if not host_hop_le(self.headers.get("Host")):
            return self._gui(403, {"loi": "Host không hợp lệ"})
        if self.path == "/":
            return self._gui(200, TRANG.encode("utf-8"), "text/html; charset=utf-8")
        if self.path == "/app.js":
            return self._gui(200, JS.encode("utf-8"), "text/javascript; charset=utf-8")
        if self.path == "/api/hop-thu":
            return self._gui(200, {"phien": self.man_hinh.danh_sach(), "phuong_moi": _phuong_moi()})
        return self._gui(404, {"loi": "không có"})

    def do_POST(self):
        if not host_hop_le(self.headers.get("Host")) or not post_hop_le(self.headers):
            return self._gui(403, {"loi": "yêu cầu không hợp lệ"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n > 65536:
                return self._gui(413, {"loi": "dữ liệu quá lớn"})
            body = json.loads(self.rfile.read(n) or b"{}")
            if not isinstance(body, dict):
                raise ValueError("cần object JSON")
        except ValueError as e:
            return self._gui(400, {"loi": "JSON hỏng: %s" % e})
        ma, sua = str(body.get("ma") or ""), body.get("sua") or {}
        if not isinstance(sua, dict):
            return self._gui(400, {"loi": "sua phải là object"})
        mh = self.man_hinh
        try:
            if self.path == "/api/kiem":
                return self._gui(200, mh.kiem(ma, sua))
            if self.path == "/api/duyet":
                return self._gui(200, mh.duyet(ma, sua))
            if self.path == "/api/huy":
                return self._gui(200, mh.huy(ma))
            if self.path == "/api/tra-loi":
                return self._gui(200, mh.them_tra_loi(ma, str(body.get("tra_loi") or "")))
        except LoiThaoTac as e:
            return self._gui(400, {"loi": str(e), "chi_tiet": e.chi_tiet})
        return self._gui(404, {"loi": "không có"})


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
    try:
        hop_thu = doc_hop_thu()
        print("Màn hình duyệt — đang xử lý %d hội thoại trong hộp thư mẫu..." % len(hop_thu))
        mh = ManHinh()
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


# ---------- giao diện (dữ liệu khách chỉ đưa vào bằng textContent / value, không dùng innerHTML) ----------

TRANG = """<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Duyệt đơn từ tin nhắn</title>
<style>
:root{
  --nen:#E9EDF1;--giay:#FFFFFF;--chat:#F4F6F8;--muc:#1C2733;--mo:#5B6876;--vien:#CCD4DD;
  --xanh:#17704A;--xanh-nhat:#E2F2EA;--vang:#9A5B00;--vang-nhat:#FFF1D2;--do:#B3261E;--do-nhat:#FBE4E2;
  --da-quang:#FFE066;--bong-shop:#D9E8FF;
  --chu-nhan:"Bahnschrift","DIN Alternate","Segoe UI",system-ui,sans-serif;
  --chu-than:"Segoe UI Variable Text","Segoe UI",system-ui,-apple-system,sans-serif;
}
*{box-sizing:border-box}
body{margin:0;font:15px/1.5 var(--chu-than);background:var(--nen);color:var(--muc)}
:focus-visible{outline:3px solid #2F6FEB;outline-offset:2px}
.phu{color:var(--mo);font-size:13px;margin:0}

.dau{display:flex;justify-content:space-between;align-items:flex-end;gap:24px;padding:18px 28px 14px;background:var(--giay);border-bottom:1px solid var(--vien)}
.dau h1{font:600 24px/1.2 var(--chu-nhan);margin:0 0 2px;letter-spacing:-.01em}
#dem{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end}

main{display:grid;grid-template-columns:300px minmax(0,1fr);gap:20px;padding:20px 28px;align-items:start}

.cot-hop-thu{background:var(--giay);border:1px solid var(--vien);border-radius:10px;overflow:hidden;position:sticky;top:20px}
.tieu-de-cot{font:600 20px/1 var(--chu-nhan);padding:16px 16px 12px;margin:0}
#loc{display:flex;gap:4px;flex-wrap:wrap;padding:0 10px 12px;border-bottom:1px solid var(--vien)}
#loc button{font:600 13px/1 var(--chu-than);padding:8px 11px;border-radius:999px;border:0;background:transparent;color:var(--mo)}
#loc button:hover{background:#EEF2F6;color:var(--muc)}
#loc button[aria-pressed="true"]{background:#E3ECF8;color:var(--muc)}
#loc .so{margin-left:5px;font:600 12px/1 var(--chu-nhan);color:var(--mo)}
#hop-thu{list-style:none;margin:0;padding:6px}
#hop-thu li{display:flex;gap:12px;align-items:center;padding:10px;border-radius:10px;cursor:pointer}
#hop-thu li:hover{background:#F2F5F8}
#hop-thu li.chon{background:#E3ECF8}
#hop-thu li.trong-loc{display:block;cursor:default;color:var(--mo);font-size:13px;text-align:center;padding:28px 10px}
#hop-thu li.trong-loc:hover{background:transparent}
.noi-dung{min-width:0;flex:1}
.dong-1{display:flex;justify-content:space-between;align-items:center;gap:8px}
.ten-khach{font-weight:600}
.xem-truoc{color:var(--mo);font-size:13px;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ma-ht{font:12px var(--chu-nhan);color:var(--mo);margin-top:3px}
.ma-ht .hoi-lai{margin-left:8px;color:var(--vang)}

.avt{flex:none;width:46px;height:46px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;overflow:hidden}
.avt svg{width:100%;height:100%;display:block}
.avt.khach{background:#DDE3EA;color:#A3AFBC}
.avt.shop{background:var(--muc);color:#fff}
.avt.shop svg{width:56%;height:56%}
.avt.vua{width:44px;height:44px}
.avt.nho{width:30px;height:30px}

.chip{font:600 12px/1 var(--chu-nhan);padding:5px 9px;border-radius:999px;white-space:nowrap}
.cho_duyet{background:var(--xanh-nhat);color:var(--xanh)}
.cho_khach{background:var(--vang-nhat);color:var(--vang)}
.tu_choi,.da_huy{background:var(--do-nhat);color:var(--do)}
.da_duyet{background:var(--muc);color:#fff}

#chi-tiet{display:grid;grid-template-columns:minmax(0,1fr) minmax(360px,440px);gap:20px;align-items:start}
.trong{grid-column:1/-1;background:var(--giay);border:1px dashed var(--vien);border-radius:10px;padding:48px;text-align:center;color:var(--mo)}

.cot-chat{background:var(--chat);border:1px solid var(--vien);border-radius:10px;padding:16px 20px 22px;min-height:420px}
.dau-chat{display:flex;gap:12px;align-items:center;padding-bottom:14px;margin-bottom:4px;border-bottom:1px solid var(--vien)}
.cot-chat h2{font:600 18px/1.25 var(--chu-nhan);margin:0}
.cot-chat .tai-khoan{margin:2px 0 0}
.nhom{display:flex;gap:8px;align-items:flex-end;margin-top:14px}
.nhom.shop{flex-direction:row-reverse}
.cac-bong{display:flex;flex-direction:column;gap:3px;max-width:78%;min-width:0}
.nhom.khach .cac-bong{align-items:flex-start}
.nhom.shop .cac-bong{align-items:flex-end}
.ten-nhom{font-size:12px;color:var(--mo);margin:0 6px 2px}
.bong{padding:9px 13px;border-radius:18px;white-space:pre-wrap;overflow-wrap:anywhere;max-width:100%}
.bong.khach{background:var(--giay);border:1px solid #DCE2E8}
.bong.shop{background:var(--bong-shop)}
.nhom.khach .bong{border-top-left-radius:6px;border-bottom-left-radius:6px}
.nhom.khach .bong:nth-child(2){border-top-left-radius:18px}
.nhom.shop .bong{border-top-right-radius:6px;border-bottom-right-radius:6px}
.nhom.shop .bong:nth-child(2){border-top-right-radius:18px}

.cot-phai{display:flex;flex-direction:column;gap:14px}
.phieu{position:relative;background:var(--giay);border:2px solid var(--muc);border-radius:6px;padding:0 0 18px}
.phieu.mo-nhat{border-color:var(--vien);color:var(--mo)}
.dau-phieu{display:flex;justify-content:space-between;align-items:baseline;gap:12px;padding:12px 18px;border-bottom:2px dashed var(--muc)}
.phieu.mo-nhat .dau-phieu{border-bottom-color:var(--vien)}
.dau-phieu h3{font:600 16px/1.2 var(--chu-nhan);margin:0}
.ma-don{font:600 15px/1 var(--chu-nhan);letter-spacing:.04em}
.van-don{font:13px/1.45 var(--chu-nhan);color:var(--mo);padding:8px 150px 0 18px;margin:0}

.quy-doi{margin:14px 18px 2px;padding:12px 14px;background:#FFFBEA;border-left:4px solid var(--da-quang);border-radius:4px}
.quy-doi .cu{display:block;color:var(--mo);font-size:13.5px;text-decoration:line-through;text-decoration-thickness:1.5px}
.quy-doi .moi{display:block;margin-top:4px;font-size:19px;line-height:1.3}
.quy-doi .mui-ten{margin-right:8px;color:var(--mo)}
.quy-doi mark{background:linear-gradient(transparent 40%,var(--da-quang) 40%,var(--da-quang) 94%,transparent 94%);color:var(--muc);font-weight:700;padding:0 3px}
.quy-doi .can-cu{display:block;font:12.5px/1.4 var(--chu-nhan);color:var(--mo);margin-top:6px}

.luoi{display:grid;grid-template-columns:96px minmax(0,1fr);gap:4px 12px;align-items:start;padding:12px 18px 0}
.luoi label,.luoi .nhan-o{padding-top:9px;color:var(--mo);font-size:13px}
.luoi input{width:100%;font:inherit;color:var(--muc);padding:7px 2px 6px;border:0;border-bottom:1.5px solid var(--vien);background:transparent;border-radius:0}
.luoi input:hover{border-bottom-color:#9AA6B2}
.luoi input:focus{border-bottom-color:var(--muc);outline:none;background:#F7F9FC}
.luoi input:focus-visible{outline:3px solid #2F6FEB;outline-offset:1px}
.luoi input.sai{border-bottom-color:var(--do);background:#FFF7F6}
.luoi .gia-tri{padding:8px 2px 6px;border-bottom:1.5px solid transparent}
.loi{color:var(--do);font-size:12.5px;margin-top:3px}
.loi:empty{display:none}

.nut{display:flex;gap:10px;padding:16px 18px 0;align-items:center}
button{font:600 14px/1 var(--chu-than);padding:10px 16px;border-radius:8px;border:1.5px solid var(--muc);background:var(--giay);color:var(--muc);cursor:pointer}
button:hover{background:#F1F4F8}
button.chinh{background:var(--xanh);border-color:var(--xanh);color:#fff;padding:10px 22px}
button.chinh:hover{background:#125C3C}
button.nhe{border-color:var(--vien);color:var(--mo)}
button:disabled{opacity:.4;cursor:not-allowed}
#bao{min-height:20px;font-size:13px;padding:10px 18px 0}

.dau-moc{position:absolute;top:60px;right:18px;font:700 20px/1 var(--chu-nhan);padding:7px 12px;border:3px solid currentColor;border-radius:6px;transform:rotate(-8deg);color:var(--xanh);background:rgba(255,255,255,.85)}
.dau-moc.huy{color:var(--do)}
.an-dong{animation:dong-dau .38s cubic-bezier(.2,.9,.3,1.25)}
@keyframes dong-dau{from{opacity:0;transform:rotate(-8deg) scale(1.7)}to{opacity:1;transform:rotate(-8deg) scale(1)}}

.hop{background:var(--giay);border:1px solid var(--vien);border-radius:10px;padding:16px 18px 18px}
.hop h3{font:600 16px/1.25 var(--chu-nhan);margin:0 0 4px}
.hop.vang{border-top:4px solid var(--vang)}
.hop.do{border-top:4px solid var(--do)}
.ghi-chu{white-space:pre-wrap;font-size:13px;color:var(--mo);margin:6px 0 0}
.nhan-tin{font-size:12px;color:var(--mo);margin:14px 0 6px}
.tin{background:var(--bong-shop);border:1.5px dashed #8FB3E8;border-radius:16px 16px 4px 16px;padding:10px 13px;white-space:pre-wrap;overflow-wrap:anywhere}
.hop .nut,.hop #bao{padding-left:0;padding-right:0}
.hop label,.them-tin label{display:block;font-size:13px;color:var(--mo);margin:16px 0 6px}
textarea{width:100%;font:inherit;padding:9px 11px;border:1.5px solid var(--vien);border-radius:8px;resize:vertical;background:var(--giay);color:var(--muc)}
textarea:focus{border-color:var(--muc);outline:none}
textarea:focus-visible{outline:3px solid #2F6FEB;outline-offset:1px}
details.them-tin{margin:0 18px;padding-top:14px}
details.them-tin summary{cursor:pointer;color:var(--mo);font-size:13px}
details.them-tin .nut{padding-left:0}

@media (max-width:1180px){#chi-tiet{grid-template-columns:1fr}}
@media (max-width:760px){main{grid-template-columns:1fr;padding:14px}.cot-hop-thu{position:static}.dau{flex-direction:column;align-items:flex-start;padding:14px}#dem{justify-content:flex-start}}
@media (prefers-reduced-motion:reduce){.an-dong{animation:none}}
</style></head><body>
<header class="dau"><div><h1>Duyệt đơn từ tin nhắn</h1>
<p class="phu">Duyệt chỉ đổi trạng thái đơn nháp, không gọi GHN và không gửi tin cho khách.</p></div>
<div id="dem" aria-live="polite"></div></header>
<main><nav class="cot-hop-thu" aria-label="Hộp thư"><p class="tieu-de-cot">Hộp thư</p><div id="loc" role="group" aria-label="Lọc hội thoại theo loại"></div><ul id="hop-thu"></ul></nav>
<section id="chi-tiet" aria-live="polite"><p class="trong">Chọn một hội thoại bên trái để xem đoạn chat và đơn nháp.</p></section></main>
<datalist id="ds-phuong"></datalist>
<script src="/app.js"></script></body></html>
"""

JS = r"""
"use strict";
const NHAN = {cho_duyet: "Đơn nháp", cho_khach: "Chờ khách", tu_choi: "Từ chối", da_duyet: "Đã duyệt", da_huy: "Đã huỷ"};
const DEM = [["cho_duyet", "đơn nháp chờ duyệt"], ["cho_khach", "chờ khách trả lời"], ["tu_choi", "từ chối"], ["da_duyet", "đã duyệt"], ["da_huy", "đã huỷ"]];
const TRUONG = [["ten_nguoi_nhan", "Người nhận"], ["sdt", "SĐT"], ["dia_chi_chi_tiet", "Địa chỉ"],
                ["phuong_xa", "Phường/xã"], ["san_pham", "Sản phẩm"], ["so_luong", "Số lượng"]];
const LOC = [["tat_ca", "Tất cả", () => true], ["cho_duyet", "Đơn nháp", p => p.trang_thai === "cho_duyet"],
             ["cho_khach", "Chờ khách", p => p.trang_thai === "cho_khach"], ["tu_choi", "Từ chối", p => p.trang_thai === "tu_choi"],
             ["xong", "Đã xử lý", p => p.trang_thai === "da_duyet" || p.trang_thai === "da_huy"]];
let phien = [], chon = null, hen = null, vuaDong = null, loc = "tat_ca";

// avatar vẽ bằng SVG dựng qua createElementNS (không tải ảnh, không dùng innerHTML)
const SVG_NS = "http://www.w3.org/2000/svg";
function hinh(tag, attrs) { const e = document.createElementNS(SVG_NS, tag); for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v); return e; }
function avt(loai, co) {
  const net = {fill: "none", stroke: "currentColor", "stroke-width": "1.7", "stroke-linejoin": "round", "stroke-linecap": "round"};
  const s = loai === "shop"
    ? hinh("svg", {viewBox: "0 0 24 24", "aria-hidden": "true", focusable: "false"})
    : hinh("svg", {viewBox: "0 0 40 40", "aria-hidden": "true", focusable: "false"});
  if (loai === "shop") s.append(hinh("path", Object.assign({d: "M4 9.5 5.6 4h12.8L20 9.5"}, net)),
    hinh("path", Object.assign({d: "M4 9.5h16v1.2a2.7 2.7 0 0 1-5.3 0 2.7 2.7 0 0 1-5.4 0 2.7 2.7 0 0 1-5.3 0z"}, net)),
    hinh("path", Object.assign({d: "M5.5 13.2V20h13v-6.8"}, net)), hinh("path", Object.assign({d: "M10 20v-4h4v4"}, net)));
  else s.append(hinh("circle", {cx: "20", cy: "15.5", r: "7.5", fill: "currentColor"}),
    hinh("path", {d: "M4.5 41c1.4-8.6 7.6-12.8 15.5-12.8S34.1 32.4 35.5 41z", fill: "currentColor"}));
  return el("span", {class: "avt " + loai + (co ? " " + co : "")}, s);
}

function el(tag, attrs, ...con) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === "text") e.textContent = v; else if (k === "on") for (const [s, f] of Object.entries(v)) e.addEventListener(s, f);
    else if (v !== null && v !== undefined && v !== false) e.setAttribute(k, v === true ? "" : v);
  }
  for (const c of con) if (c) e.append(c);
  return e;
}
async function goi(duong, body) {
  const r = await fetch(duong, body === undefined ? {} : {method: "POST",
    headers: {"Content-Type": "application/json", "X-Man-Hinh-Duyet": "1"}, body: JSON.stringify(body)});
  const d = await r.json();
  if (!r.ok) { const e = new Error(d.loi || r.statusText); e.chi_tiet = d.chi_tiet; throw e; }
  return d;
}
// `ma`: hội thoại phát ra thông báo — kết quả về muộn của hội thoại khác thì không hiện lên khung đang xem
function bao(text, sai, ma) { if (ma && ma !== chon) return; const b = document.getElementById("bao"); if (b) { b.textContent = text; b.style.color = sai ? "var(--do)" : "var(--xanh)"; } }

async function tai(giu) {
  const d = await goi("/api/hop-thu");
  phien = d.phien;
  const dl = document.getElementById("ds-phuong"); dl.replaceChildren(...d.phuong_moi.map(p => el("option", {value: p})));
  veHopThu();
  if (giu && chon) veChiTiet(phien.find(p => p.ma_hoi_thoai === chon));
}
// cập nhật dữ liệu của p; chỉ vẽ lại khung chi tiết khi p vẫn là hội thoại đang chọn (kết quả có thể về muộn)
function capNhat(p) { const i = phien.findIndex(x => x.ma_hoi_thoai === p.ma_hoi_thoai); if (i >= 0) phien[i] = p; veHopThu(); if (p.ma_hoi_thoai === chon) veChiTiet(p); }

function cacLuot(text) {  // "Mã khách: KH-1 | Khách: … | Shop: …" → [{ai, nd}]
  return (text ? text.split(" | ") : []).map(l => { const i = l.indexOf(": "); return i > 0 ? {ai: l.slice(0, i), nd: l.slice(i + 2)} : {ai: "", nd: l}; });
}
function tinKhachCuoi(p) { const k = cacLuot(p.text).filter(l => l.ai === "Khách"); return k.length ? k[k.length - 1].nd : ""; }

function veHopThu() {
  // vẽ lại cả danh sách thì phần tử đang focus bị thay: nhớ dòng / tab đang focus rồi trả focus về đó
  const a = document.activeElement && document.activeElement.closest ? document.activeElement : null;
  const maFocus = a && a.closest("#hop-thu li") ? a.closest("#hop-thu li").getAttribute("data-ma") : null;
  const locFocus = a && a.closest("#loc button") ? a.closest("#loc button").getAttribute("data-loc") : null;
  document.getElementById("dem").replaceChildren(...DEM.map(([t, chu]) => {
    const n = phien.filter(p => p.trang_thai === t).length;
    return n ? el("span", {class: "chip " + t, text: n + " " + chu}) : null;
  }).filter(Boolean));
  const tab = document.getElementById("loc");
  tab.replaceChildren(...LOC.map(([k, ten, f]) => el("button", {type: "button", "data-loc": k, "aria-pressed": k === loc ? "true" : "false",
      on: {click: () => { loc = k; veHopThu(); }}}, document.createTextNode(ten), el("span", {class: "so", text: String(phien.filter(f).length)}))));
  const hien = phien.filter(LOC.find(x => x[0] === loc)[2]);
  const ds = document.getElementById("hop-thu");
  ds.replaceChildren(...(hien.length ? hien.map(p => el("li", {class: p.ma_hoi_thoai === chon ? "chon" : null, "data-ma": p.ma_hoi_thoai,
      tabindex: "0", "aria-current": p.ma_hoi_thoai === chon ? "true" : null,
      on: {click: () => chonHoiThoai(p.ma_hoi_thoai), keydown: e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); chonHoiThoai(p.ma_hoi_thoai); } }}},
    avt("khach"),
    el("div", {class: "noi-dung"},
      el("div", {class: "dong-1"}, el("span", {class: "ten-khach", text: p.ma_khach || "Khách mới"}), el("span", {class: "chip " + p.trang_thai, text: NHAN[p.trang_thai]})),
      el("div", {class: "xem-truoc", text: p.loi_doc ? "Không đọc được hội thoại này" : tinKhachCuoi(p)}),
      el("div", {class: "ma-ht"}, document.createTextNode(p.ma_hoi_thoai),
        p.so_luot_hoi_lai ? el("span", {class: "hoi-lai", text: "hỏi lại " + p.so_luot_hoi_lai + " lần"}) : null))))
    : [el("li", {class: "trong-loc", text: "Không có hội thoại nào ở mục này."})]));
  if (maFocus) { const li = [...ds.children].find(x => x.getAttribute("data-ma") === maFocus); if (li) li.focus(); }
  if (locFocus) { const b = [...tab.children].find(x => x.getAttribute("data-loc") === locFocus); if (b) b.focus(); }
}
function chonHoiThoai(ma) { clearTimeout(hen); chon = ma; veHopThu(); veChiTiet(phien.find(p => p.ma_hoi_thoai === ma)); }

function quyDoi(kq) {  // dòng "Phường/xã: <mới> (quy đổi từ <cũ> theo khoản <N> Nghị quyết …[; khách chọn])"
  const d = (kq.cho_chu_shop || "").split("\n").find(x => x.startsWith("Phường/xã:"));
  const m = d && d.match(/^Phường\/xã: (.*) \(quy đổi từ (.*) theo (khoản .*?)(; khách chọn)?\)$/);
  return m ? {moi: m[1], cu: m[2], can_cu: m[3], khach_chon: !!m[4]} : null;
}
function dongQuyDoi(q) {
  return el("div", {class: "quy-doi", id: "qd"},
    el("span", {class: "cu", text: q.cu}), el("span", {class: "moi"}, el("span", {class: "mui-ten", text: "→", "aria-hidden": "true"}), el("mark", {text: q.moi})),
    el("span", {class: "can-cu", text: "Quy đổi theo " + q.can_cu + (q.khach_chon ? ", phường do khách chọn" : "")}));
}

function veChiTiet(p) {
  const ct = document.getElementById("chi-tiet");
  if (!p) { ct.replaceChildren(el("p", {class: "trong", text: "Chọn một hội thoại bên trái để xem đoạn chat và đơn nháp."})); return; }
  const luot = cacLuot(p.text), tk = luot.find(l => l.ai === "Mã khách");
  const chat = el("div", {class: "cot-chat"}, el("div", {class: "dau-chat"}, avt("khach", "vua"),
    el("div", {}, el("h2", {text: "Hội thoại với " + (p.ma_khach || "khách mới")}),
      el("p", {class: "phu tai-khoan", text: tk ? "Tài khoản chat " + tk.nd + ", mã hội thoại " + p.ma_hoi_thoai : "Khách chưa có tài khoản, mã hội thoại " + p.ma_hoi_thoai}))));
  if (p.loi_doc) chat.append(el("p", {class: "loi", text: "Không đọc được dòng này trong hộp thư: " + p.loi_doc}));
  let nhom = null, truoc = null;  // tin liền nhau của cùng một người gom thành một nhóm, avatar cạnh nhóm
  for (const l of luot) {
    if (l.ai === "Mã khách") continue;
    const shop = l.ai === "Shop";
    if (l.ai !== truoc) {
      nhom = el("div", {class: "cac-bong"}, el("p", {class: "ten-nhom", text: shop ? "Shop" : (l.ai || "Tin nhắn")}));
      chat.append(el("div", {class: "nhom " + (shop ? "shop" : "khach")}, avt(shop ? "shop" : "khach", "nho"), nhom));
    }
    nhom.append(el("div", {class: "bong " + (shop ? "shop" : "khach"), text: l.nd}));
    truoc = l.ai;
  }
  const phai = el("div", {class: "cot-phai"});
  if (p.trang_thai === "cho_duyet") phai.append(veDon(p));
  else if (p.trang_thai === "da_duyet" || p.trang_thai === "da_huy") phai.append(veDaXong(p));
  else phai.append(veChoKhach(p));
  ct.replaceChildren(chat, phai);
}

function veDaXong(p) {
  const duyet = p.trang_thai === "da_duyet", t = p.truong_duyet || p.kq.truong || {};
  const phieu = el("article", {class: "phieu" + (duyet ? "" : " mo-nhat")},
    el("div", {class: "dau-phieu"}, el("h3", {text: duyet ? "Phiếu giao hàng" : "Đơn nháp đã huỷ"}), el("span", {class: "ma-don", text: p.ma_don || ""})));
  if (duyet) phieu.append(el("p", {class: "van-don", text: "Mã đơn " + p.ma_don + ", vận đơn nháp " + p.ma_van_don +
    (p.truong_da_sua && p.truong_da_sua.length ? ", chủ shop đã sửa " + p.truong_da_sua.length + " trường" : ", duyệt không cần sửa")}));
  const q = quyDoi(p.kq);  // giữ dải quy đổi khi chủ shop không sửa phường
  if (duyet && q && !(p.truong_da_sua || []).includes("phuong_xa")) phieu.append(dongQuyDoi(q));
  const luoi = el("div", {class: "luoi"});
  for (const [k, nhan] of TRUONG) luoi.append(el("span", {class: "nhan-o", text: nhan}), el("div", {class: "gia-tri", text: t[k] == null ? "" : String(t[k])}));
  luoi.append(el("span", {class: "nhan-o", text: "Tỉnh/thành"}), el("div", {class: "gia-tri", text: t.tinh_thanh || ""}));
  const dau = el("div", {class: "dau-moc" + (duyet ? "" : " huy") + (vuaDong === p.ma_hoi_thoai ? " an-dong" : ""), text: duyet ? "Đã duyệt" : "Đã huỷ"});
  vuaDong = null;
  phieu.append(luoi, dau);
  return phieu;
}

function veDon(p) {
  const t = p.kq.truong, o = {}, q = quyDoi(p.kq);
  const duyet = el("button", {class: "chinh", text: "Duyệt"}), huy = el("button", {class: "nhe", text: "Huỷ"});
  const phieu = el("article", {class: "phieu", "aria-label": "Đơn nháp " + p.ma_don},
    el("div", {class: "dau-phieu"}, el("h3", {text: "Phiếu giao hàng nháp"}), el("span", {class: "ma-don", text: p.ma_don})));
  const dai = q ? dongQuyDoi(q) : null;  // giữ tham chiếu dải quy đổi của chính phiếu này
  if (dai) phieu.append(dai);
  let lanKiem = 0;  // chỉ áp kết quả của lần kiểm mới nhất
  const luoi = el("div", {class: "luoi"});
  for (const [k, nhan] of TRUONG) {
    const inp = el("input", {id: "f-" + k, value: t[k] === null || t[k] === undefined ? "" : String(t[k]),
      list: k === "phuong_xa" ? "ds-phuong" : null, inputmode: k === "sdt" || k === "so_luong" ? "numeric" : null, autocomplete: "off",
      on: {input: () => { clearTimeout(hen); duyet.disabled = true; hen = setTimeout(kiem, 300); }}});
    const loi = el("div", {class: "loi", "aria-live": "polite"});
    o[k] = {inp, loi}; luoi.append(el("label", {for: "f-" + k, text: nhan}), el("div", {}, inp, loi));
  }
  luoi.append(el("span", {class: "nhan-o", text: "Tỉnh/thành"}), el("div", {class: "gia-tri", text: t.tinh_thanh || ""}));
  const sua = () => Object.fromEntries(TRUONG.map(([k]) => [k, o[k].inp.value]));
  async function kiem() {
    const lan = ++lanKiem;
    try {
      const k = await goi("/api/kiem", {ma: p.ma_hoi_thoai, sua: sua()});
      if (lan !== lanKiem) return;  // đã có lần kiểm mới hơn trên phiếu này
      for (const [f] of TRUONG) {
        const l = k.loi[f] || "", g = (k.goi_y[f] || []).length ? ". Gần giống: " + k.goi_y[f].join(", ") : "";
        o[f].loi.textContent = l ? l + g : ""; o[f].inp.classList.toggle("sai", !!l);
      }
      if (dai) dai.hidden = k.truong_da_sua.includes("phuong_xa");
      duyet.disabled = !k.duoc_duyet;
      bao(k.duoc_duyet ? (k.truong_da_sua.length ? "Đã sửa " + k.truong_da_sua.length + " trường, đơn vẫn qua kiểm" : "") : "Còn trường chưa qua kiểm, chưa duyệt được", !k.duoc_duyet, p.ma_hoi_thoai);
    } catch (e) { if (lan === lanKiem) bao(e.message, true, p.ma_hoi_thoai); }
  }
  duyet.addEventListener("click", async () => {
    duyet.disabled = true;
    try { const r = await goi("/api/duyet", {ma: p.ma_hoi_thoai, sua: sua()}); vuaDong = r.ma_hoi_thoai; capNhat(r); }
    catch (e) { bao(e.message, true, p.ma_hoi_thoai); if (chon === p.ma_hoi_thoai) kiem(); }
  });
  huy.addEventListener("click", async () => {
    if (!confirm("Huỷ đơn nháp " + p.ma_don + "?")) return;
    try { const r = await goi("/api/huy", {ma: p.ma_hoi_thoai}); vuaDong = r.ma_hoi_thoai; capNhat(r); } catch (e) { bao(e.message, true, p.ma_hoi_thoai); }
  });
  phieu.append(luoi, el("div", {class: "nut"}, duyet, huy), el("div", {id: "bao", role: "status"}));
  phieu.append(el("details", {class: "them-tin"}, el("summary", {text: "Khách nhắn thêm sau khi chốt đơn"}), ...oTraLoi(p, "Dán tin khách vừa nhắn")));
  setTimeout(kiem, 0);
  return phieu;
}

function oTraLoi(p, goiY) {
  const o = el("textarea", {rows: "2", id: "tra-loi", placeholder: goiY}), them = el("button", {text: "Thêm vào hội thoại"});
  them.addEventListener("click", async () => {
    if (!o.value.trim()) { bao("Câu khách trả lời đang trống", true); return; }
    them.disabled = true; bao("Đang đọc lại cả hội thoại...");
    try { capNhat(await goi("/api/tra-loi", {ma: p.ma_hoi_thoai, tra_loi: o.value})); } catch (e) { bao(e.message, true, p.ma_hoi_thoai); them.disabled = false; }
  });
  return [el("label", {for: "tra-loi", text: "Khách trả lời"}), o, el("div", {class: "nut"}, them)];
}

function veChoKhach(p) {
  const tuChoi = p.trang_thai === "tu_choi", tin = p.kq.tin_gui_khach || "";
  const hop = el("section", {class: "hop " + (tuChoi ? "do" : "vang")},
    el("h3", {text: tuChoi ? "Đã từ chối, chưa tạo đơn" : "Cần hỏi lại khách trước khi lên đơn"}),
    el("p", {class: "ghi-chu", text: p.kq.cho_chu_shop}));
  if (tin) {
    const chep = el("button", {text: "Chép"});
    chep.addEventListener("click", async () => { try { await navigator.clipboard.writeText(tin); bao("Đã chép tin gửi khách", false, p.ma_hoi_thoai); } catch (e) { bao("Không chép được: " + e.message, true, p.ma_hoi_thoai); } });
    hop.append(el("p", {class: "nhan-tin", text: "Tin soạn sẵn, shop chép rồi tự gửi cho khách"}), el("div", {class: "tin", text: tin}), el("div", {class: "nut"}, chep));
  } else {
    hop.append(el("p", {class: "nhan-tin", text: "Không có tin soạn sẵn vì lỗi hệ thống. Shop tự nhắn khách."}));
  }
  hop.append(...oTraLoi(p, "Dán câu khách vừa trả lời"), el("div", {id: "bao", role: "status"}));
  return hop;
}

tai(false).catch(e => { document.getElementById("chi-tiet").replaceChildren(el("p", {class: "trong", text: "Không tải được hộp thư: " + e.message})); });
"""


if __name__ == "__main__":
    sys.exit(main())
