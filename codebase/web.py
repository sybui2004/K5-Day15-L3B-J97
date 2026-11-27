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
            p.update(trang_thai="da_duyet", ma_don=don["ma_don"], ma_van_don=don["ma_van_don"],
                     truong_duyet=k["truong"], truong_da_sua=k["truong_da_sua"])
            self._ghi(p, "da_duyet", k["truong_da_sua"])
            return copy.deepcopy(p)

    def huy(self, ma):
        with self._khoa:
            p = self._lay(ma)
            if p["trang_thai"] in DA_XONG:
                raise LoiThaoTac("hội thoại %s đã %s" % (ma, "duyệt" if p["trang_thai"] == "da_duyet" else "huỷ"))
            p["trang_thai"] = "da_huy"
            self._ghi(p, "da_huy", [])
            return copy.deepcopy(p)

    def them_tra_loi(self, ma, tra_loi):
        """Luồng B: ghép câu khách trả lời rồi chạy lại xu_ly. Model lỗi thì giữ nguyên hội thoại để thử lại."""
        with self._khoa:
            p = self._lay(ma)
            if p["trang_thai"] in DA_XONG:
                raise LoiThaoTac("hội thoại %s đã xong, không thêm trả lời được" % ma)
            if p["loi_doc"] or not p["text"]:
                raise LoiThaoTac("hội thoại %s không đọc được từ hộp thư, shop xử lý tay" % ma)
            try:
                text = ghep_tra_loi(p["text"], p["kq"]["tin_gui_khach"], tra_loi)
            except ValueError as e:
                raise LoiThaoTac(str(e))
            try:
                kq = _co_trace("web:" + ma, xu_ly, text, ma)
            except Exception as e:  # model lỗi, mất mạng…
                raise LoiThaoTac("chưa xử lý được câu trả lời (%s: %s), thử lại sau" % (type(e).__name__, e))
            p.update(text=text, kq=kq, trang_thai=TRANG_THAI.get(kq["quyet_dinh"], "cho_khach"),
                     so_luot_hoi_lai=p["so_luot_hoi_lai"] + 1, ma_don=kq.get("ma_don"),
                     ma_van_don=kq.get("ma_van_don"))
            return copy.deepcopy(p)

    def _ghi(self, p, ket_qua, da_sua):
        ghi_nhat_ky(self.nhat_ky, {"ma_hoi_thoai": p["ma_hoi_thoai"], "quyet_dinh_ai": p["kq"]["quyet_dinh"],
                                   "truong_da_sua": da_sua, "so_luot_hoi_lai": p["so_luot_hoi_lai"],
                                   "ket_qua": ket_qua, "luc": time.strftime("%Y-%m-%dT%H:%M:%S")})


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


def main() -> int:
    hop_thu = doc_hop_thu()
    print("Màn hình duyệt — đang xử lý %d hội thoại trong hộp thư mẫu..." % len(hop_thu))
    mh = ManHinh()
    mh.tai(hop_thu)
    XuLyYeuCau.man_hinh = mh
    try:
        server = HTTPServer((HOST, PORT), XuLyYeuCau)
    except OSError as e:
        print("Không mở được %s:%d (%s). Cổng đang bận? Tắt chương trình đang dùng cổng rồi chạy lại." % (HOST, PORT, e))
        return 1
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
:root{--nen:#f6f6f4;--the:#fff;--chu:#1d1d1b;--mo:#6b6b66;--vien:#dcdcd6;--xanh:#1f6f4a;--do:#b3261e;--vang:#8a5a00}
*{box-sizing:border-box}body{margin:0;font:15px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif;background:var(--nen);color:var(--chu)}
header{padding:12px 20px;border-bottom:1px solid var(--vien);background:var(--the);display:flex;gap:16px;align-items:baseline}
header h1{font-size:17px;margin:0}header span{color:var(--mo);font-size:13px}
main{display:grid;grid-template-columns:300px 1fr;gap:16px;padding:16px 20px;max-width:1200px}
.khung{background:var(--the);border:1px solid var(--vien);border-radius:8px}
#hop-thu{list-style:none;margin:0;padding:6px}#hop-thu li{padding:9px 10px;border-radius:6px;cursor:pointer;display:flex;justify-content:space-between;gap:8px}
#hop-thu li:hover{background:#efefea}#hop-thu li.chon{background:#e4ece7}
.nhan{font-size:12px;font-weight:600;letter-spacing:.02em;white-space:nowrap}
.cho_duyet{color:var(--xanh)}.cho_khach{color:var(--vang)}.tu_choi,.da_huy{color:var(--do)}.da_duyet{color:var(--mo)}
.phu{color:var(--mo);font-size:12px}
#chi-tiet{padding:16px 18px;min-height:300px}h2{font-size:15px;margin:0 0 10px}h3{font-size:14px;margin:18px 0 8px;padding-top:12px;border-top:1px solid var(--vien)}
.luot{padding:3px 0}.luot b{font-weight:600;margin-right:4px}.luot.shop{color:var(--mo)}
.luoi{display:grid;grid-template-columns:110px 1fr;gap:8px 10px;align-items:start;max-width:620px}
label{padding-top:6px;color:var(--mo);font-size:13px}input,textarea{width:100%;font:inherit;padding:6px 8px;border:1px solid var(--vien);border-radius:6px}
input.sai{border-color:var(--do)}.loi{color:var(--do);font-size:12px;margin-top:2px}.goc{font-size:12px;color:var(--mo);margin-top:2px}
button{font:inherit;padding:7px 14px;border-radius:6px;border:1px solid var(--vien);background:var(--the);cursor:pointer}
button.chinh{background:var(--xanh);border-color:var(--xanh);color:#fff}button:disabled{opacity:.45;cursor:not-allowed}
.nut{display:flex;gap:8px;margin-top:12px}.tin{background:#f3f1ea;border-radius:6px;padding:8px 10px;white-space:pre-wrap}
.ghi-chu{white-space:pre-wrap;font-size:13px;color:var(--mo)}#bao{min-height:20px;margin-top:8px;font-size:13px}
</style></head><body>
<header><h1>Duyệt đơn từ tin nhắn</h1><span>Duyệt chỉ đổi trạng thái đơn nháp: không gọi GHN, không gửi tin cho khách.</span></header>
<main><section class="khung"><ul id="hop-thu"></ul></section><section class="khung" id="chi-tiet"><p class="phu">Chọn một hội thoại.</p></section></main>
<datalist id="ds-phuong"></datalist>
<script src="/app.js"></script></body></html>
"""

JS = r"""
"use strict";
const NHAN = {cho_duyet: "ĐƠN NHÁP", cho_khach: "CHỜ KHÁCH", tu_choi: "TỪ CHỐI", da_duyet: "ĐÃ DUYỆT", da_huy: "ĐÃ HUỶ"};
const DAU = {cho_duyet: "●", cho_khach: "○", tu_choi: "✕", da_duyet: "✓", da_huy: "–"};
const TRUONG = [["ten_nguoi_nhan", "Người nhận"], ["sdt", "SĐT"], ["dia_chi_chi_tiet", "Địa chỉ"],
                ["phuong_xa", "Phường/xã"], ["san_pham", "Sản phẩm"], ["so_luong", "Số lượng"]];
let phien = [], chon = null, hen = null;

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
function bao(text, sai) { const b = document.getElementById("bao"); if (b) { b.textContent = text; b.style.color = sai ? "var(--do)" : "var(--xanh)"; } }

async function tai(giu) {
  const d = await goi("/api/hop-thu");
  phien = d.phien;
  const dl = document.getElementById("ds-phuong"); dl.replaceChildren(...d.phuong_moi.map(p => el("option", {value: p})));
  veHopThu();
  if (giu && chon) veChiTiet(phien.find(p => p.ma_hoi_thoai === chon));
}
function capNhat(p) { const i = phien.findIndex(x => x.ma_hoi_thoai === p.ma_hoi_thoai); if (i >= 0) phien[i] = p; veHopThu(); veChiTiet(p); }

function veHopThu() {
  document.getElementById("hop-thu").replaceChildren(...phien.map(p => el("li", {class: p.ma_hoi_thoai === chon ? "chon" : null,
      on: {click: () => { chon = p.ma_hoi_thoai; veHopThu(); veChiTiet(p); }}},
    el("span", {}, el("span", {text: DAU[p.trang_thai] + " " + (p.ma_khach || p.ma_hoi_thoai)}),
      el("br"), el("span", {class: "phu", text: p.ma_hoi_thoai + (p.so_luot_hoi_lai ? " · hỏi lại " + p.so_luot_hoi_lai + " lượt" : "")})),
    el("span", {class: "nhan " + p.trang_thai, text: NHAN[p.trang_thai]}))));
}

function dongPhuong(kq) {
  const d = (kq.cho_chu_shop || "").split("\n").find(x => x.startsWith("Phường/xã:"));
  const m = d && d.match(/\((quy đổi từ .*)\)$/); return m ? m[1] : "";
}

function veChiTiet(p) {
  const ct = document.getElementById("chi-tiet");
  if (!p) { ct.replaceChildren(el("p", {class: "phu", text: "Chọn một hội thoại."})); return; }
  const kq = p.kq, khoi = [el("h2", {text: "Hội thoại " + (p.ma_khach || "khách mới") + " · " + p.ma_hoi_thoai})];
  if (p.loi_doc) khoi.push(el("p", {class: "loi", text: "Không đọc được dòng này trong hộp thư: " + p.loi_doc}));
  for (const l of (p.text ? p.text.split(" | ") : [])) {
    const i = l.indexOf(": "), ai = i > 0 ? l.slice(0, i) : "", nd = i > 0 ? l.slice(i + 2) : l;
    khoi.push(el("div", {class: "luot" + (ai === "Shop" ? " shop" : "")}, el("b", {text: ai ? ai + ":" : ""}), document.createTextNode(nd)));
  }
  if (p.trang_thai === "cho_duyet") khoi.push(...veDon(p));
  if (p.trang_thai === "da_duyet" || p.trang_thai === "da_huy") {
    khoi.push(el("h3", {text: p.trang_thai === "da_duyet" ? "Đã duyệt" : "Đã huỷ"}));
    if (p.trang_thai === "da_duyet") khoi.push(el("p", {text: "Mã đơn " + p.ma_don + " · Vận đơn nháp " + p.ma_van_don +
      (p.truong_da_sua && p.truong_da_sua.length ? " · đã sửa: " + p.truong_da_sua.join(", ") : " · không sửa")}));
  }
  if (p.trang_thai !== "cho_duyet" && p.trang_thai !== "da_duyet" && p.trang_thai !== "da_huy") khoi.push(el("p", {class: "ghi-chu", text: kq.cho_chu_shop}));
  if (p.trang_thai !== "da_duyet" && p.trang_thai !== "da_huy") khoi.push(...veChoKhach(p));
  khoi.push(el("div", {id: "bao"}));
  ct.replaceChildren(...khoi);
}

function veDon(p) {
  const t = p.kq.truong, o = {}, ra = [el("h3", {text: "Đơn nháp " + p.ma_don})], luoi = el("div", {class: "luoi"});
  const qd = dongPhuong(p.kq), duyet = el("button", {class: "chinh", text: "Duyệt"}), huy = el("button", {text: "Huỷ"});
  for (const [k, nhan] of TRUONG) {
    const inp = el("input", {id: "f-" + k, value: t[k] === null || t[k] === undefined ? "" : String(t[k]),
      list: k === "phuong_xa" ? "ds-phuong" : null, inputmode: k === "sdt" || k === "so_luong" ? "numeric" : null,
      on: {input: () => { clearTimeout(hen); duyet.disabled = true; hen = setTimeout(kiem, 300); }}});
    const loi = el("div", {class: "loi"}), o_ = el("div", {}, inp, loi);
    if (k === "phuong_xa" && qd) o_.append(el("div", {class: "goc", id: "qd", text: qd}));
    o[k] = {inp, loi}; luoi.append(el("label", {for: "f-" + k, text: nhan}), o_);
  }
  luoi.append(el("label", {text: "Tỉnh/thành"}), el("div", {style: "padding-top:6px", text: t.tinh_thanh || ""}));
  const sua = () => Object.fromEntries(TRUONG.map(([k]) => [k, o[k].inp.value]));
  async function kiem() {
    try {
      const k = await goi("/api/kiem", {ma: p.ma_hoi_thoai, sua: sua()});
      for (const [f] of TRUONG) {
        const l = k.loi[f] || "", g = (k.goi_y[f] || []).length ? " · gần giống: " + k.goi_y[f].join(", ") : "";
        o[f].loi.textContent = l ? l + g : ""; o[f].inp.classList.toggle("sai", !!l);
      }
      const q = document.getElementById("qd"); if (q) q.hidden = k.truong_da_sua.includes("phuong_xa");
      duyet.disabled = !k.duoc_duyet;
      bao(k.duoc_duyet ? (k.truong_da_sua.length ? "Đã sửa: " + k.truong_da_sua.join(", ") + " · qua kiểm" : "") : "Còn trường chưa qua kiểm, chưa duyệt được", !k.duoc_duyet);
    } catch (e) { bao(e.message, true); }
  }
  duyet.addEventListener("click", async () => {
    duyet.disabled = true;
    try { capNhat(await goi("/api/duyet", {ma: p.ma_hoi_thoai, sua: sua()})); } catch (e) { bao(e.message, true); kiem(); }
  });
  huy.addEventListener("click", async () => {
    if (!confirm("Huỷ đơn nháp " + p.ma_don + "?")) return;
    try { capNhat(await goi("/api/huy", {ma: p.ma_hoi_thoai})); } catch (e) { bao(e.message, true); }
  });
  ra.push(luoi, el("div", {class: "nut"}, duyet, huy));
  setTimeout(kiem, 0);
  return ra;
}

function veChoKhach(p) {
  const tin = p.kq.tin_gui_khach || "", ra = [el("h3", {text: p.trang_thai === "cho_duyet" ? "Khách nhắn thêm" : "Chờ khách (luồng B)"})];
  if (tin && p.trang_thai !== "cho_duyet") {
    const chep = el("button", {text: "Chép"});
    chep.addEventListener("click", async () => { try { await navigator.clipboard.writeText(tin); bao("Đã chép tin gửi khách"); } catch (e) { bao("Không chép được: " + e.message, true); } });
    ra.push(el("div", {class: "phu", text: "Tin gửi khách (shop tự gửi):"}), el("div", {class: "tin", text: tin}), el("div", {class: "nut"}, chep));
  } else if (!tin && p.trang_thai === "cho_khach") {
    ra.push(el("p", {class: "phu", text: "Không có tin soạn sẵn (lỗi hệ thống) — shop tự nhắn khách."}));
  }
  const o = el("textarea", {rows: "2", id: "tra-loi", placeholder: "Dán câu khách trả lời"}), them = el("button", {text: "Thêm"});
  them.addEventListener("click", async () => {
    if (!o.value.trim()) { bao("Câu khách trả lời đang trống", true); return; }
    them.disabled = true; bao("Đang xử lý lại hội thoại...");
    try { capNhat(await goi("/api/tra-loi", {ma: p.ma_hoi_thoai, tra_loi: o.value})); } catch (e) { bao(e.message, true); them.disabled = false; }
  });
  ra.push(el("label", {for: "tra-loi", text: "Khách trả lời:"}), o, el("div", {class: "nut"}, them));
  return ra;
}

tai(false).catch(e => { document.getElementById("chi-tiet").replaceChildren(el("p", {class: "loi", text: "Không tải được hộp thư: " + e.message})); });
"""


if __name__ == "__main__":
    sys.exit(main())
