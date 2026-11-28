"""Tài khoản khách và shop cho bản demo: mật khẩu băm scrypt, phiên đăng nhập, giới hạn tần suất.

Thiết kế: docs/superpowers/specs/2026-11-28-chat-khach-hitl-design.md (§5.1–§5.3).
- Khách tự đăng ký; lưu ở kho (codebase/kho.py). Shop chỉ có một tài khoản `admin`, mật khẩu từ ADMIN_PASSWORD,
  không lưu ở kho; phiên của shop giữ trong bộ nhớ (khởi động lại thì đăng nhập lại).
- Token phiên chỉ lưu dạng băm SHA-256; cookie giữ token gốc.
Chỉ dùng thư viện chuẩn.
"""
import collections
import hashlib
import hmac
import re
import secrets
import threading
import time

from kho import TrungTen

HET_HAN_PHIEN = 43200  # 12 giờ
GIOI_HAN_DANG_KY = (5, 3600)        # tài khoản / IP / giờ (người xem dùng 4G)
GIOI_HAN_DANG_NHAP_SAI = (10, 600)  # lần sai / (IP, username) / 10 phút
ADMIN = "admin"
_USERNAME = re.compile(r"^[a-z0-9_.]{3,32}$")
_SCRYPT = {"n": 2 ** 14, "r": 8, "p": 1, "dklen": 32}


class LoiDangNhap(ValueError):
    """Đăng ký / đăng nhập không hợp lệ (thông báo đưa thẳng cho người dùng)."""


class QuaGioiHan(Exception):
    def __init__(self, cho_giay):
        super().__init__("gửi nhanh quá, thử lại sau %d giây" % cho_giay)
        self.cho_giay = int(cho_giay)


def bam_mat_khau(mk: str) -> str:
    muoi = secrets.token_bytes(16)
    return "scrypt$%s$%s" % (muoi.hex(), hashlib.scrypt(mk.encode("utf-8"), salt=muoi, **_SCRYPT).hex())


def kiem_mat_khau(mk: str, bam: str) -> bool:
    try:
        loai, muoi, gia_tri = bam.split("$")
        if loai != "scrypt":
            return False
        thu = hashlib.scrypt(mk.encode("utf-8"), salt=bytes.fromhex(muoi), **_SCRYPT).hex()
    except ValueError:
        return False
    return hmac.compare_digest(thu, gia_tri)


def bam_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class GioiHan:
    """Cửa sổ trượt: tối đa `so` lần trong `giay` giây cho mỗi khoá. An toàn luồng."""

    def __init__(self, so: int, giay: float):
        self.so, self.giay = so, giay
        self._lan = collections.defaultdict(collections.deque)
        self._khoa = threading.Lock()

    def _don(self, q, bay_gio):
        while q and q[0] <= bay_gio - self.giay:
            q.popleft()

    def dung(self, khoa: str, bay_gio=None) -> None:
        """Ghi một lần dùng; quá số lần thì ném QuaGioiHan (không ghi)."""
        bay_gio = time.time() if bay_gio is None else bay_gio
        with self._khoa:
            q = self._lan[khoa]
            self._don(q, bay_gio)
            if len(q) >= self.so:
                raise QuaGioiHan(max(1, q[0] + self.giay - bay_gio))
            q.append(bay_gio)

    def kiem(self, khoa: str, bay_gio=None) -> None:
        """Như dung() nhưng không ghi: dùng để chặn trước khi biết lần này có tính không."""
        bay_gio = time.time() if bay_gio is None else bay_gio
        with self._khoa:
            q = self._lan[khoa]
            self._don(q, bay_gio)
            if len(q) >= self.so:
                raise QuaGioiHan(max(1, q[0] + self.giay - bay_gio))


class QuanLyTaiKhoan:
    def __init__(self, kho, mat_khau_admin: str):
        self.kho = kho
        self._mat_khau_admin = mat_khau_admin
        self._phien_admin = {}  # token_bam → hạn
        self._khoa = threading.Lock()
        self._dang_ky = GioiHan(*GIOI_HAN_DANG_KY)
        self._sai = GioiHan(*GIOI_HAN_DANG_NHAP_SAI)

    @staticmethod
    def _chuan_username(username) -> str:
        return str(username or "").strip().lower()

    def dang_ky(self, username, mat_khau, nhap_lai, ip) -> dict:
        u = self._chuan_username(username)
        if not _USERNAME.match(u):
            raise LoiDangNhap("tên đăng nhập 3–32 ký tự, chỉ gồm chữ thường không dấu, số, dấu _ và dấu .")
        if u == ADMIN:
            raise LoiDangNhap("tên đăng nhập này không dùng được")
        mk = str(mat_khau or "")
        if not 6 <= len(mk) <= 128:
            raise LoiDangNhap("mật khẩu 6–128 ký tự")
        if mk != str(nhap_lai or ""):
            raise LoiDangNhap("mật khẩu nhập lại không khớp")
        self._dang_ky.kiem("ip:" + str(ip))
        try:
            i = self.kho.tao_tai_khoan(u, bam_mat_khau(mk), "khach", str(ip))
        except TrungTen:
            raise LoiDangNhap("tên đăng nhập đã có người dùng")
        self._dang_ky.dung("ip:" + str(ip))
        return {"id": i, "username": u, "vai": "khach"}

    def dang_nhap(self, username, mat_khau, ip) -> dict:
        u = self._chuan_username(username)
        khoa_sai = "%s|%s" % (ip, u)
        self._sai.kiem(khoa_sai)
        mk = str(mat_khau or "")
        if u == ADMIN:
            if hmac.compare_digest(mk.encode("utf-8"), self._mat_khau_admin.encode("utf-8")):
                return {"id": 0, "username": ADMIN, "vai": "shop"}
        else:
            t = self.kho.tim_tai_khoan(u)
            if t and kiem_mat_khau(mk, t["mat_khau_bam"]):
                return {"id": t["id"], "username": t["username"], "vai": t["vai"]}
        self._sai.dung(khoa_sai)
        raise LoiDangNhap("sai tên đăng nhập hoặc mật khẩu")

    def tao_phien(self, tk: dict) -> str:
        token = secrets.token_urlsafe(32)
        het_han = time.time() + HET_HAN_PHIEN
        if tk["vai"] == "shop":
            with self._khoa:
                self._phien_admin[bam_token(token)] = het_han
        else:
            self.kho.luu_phien(bam_token(token), tk["id"], het_han)
        return token

    def doc_phien(self, token) -> dict | None:
        if not token:
            return None
        b = bam_token(str(token))
        with self._khoa:
            han = self._phien_admin.get(b)
            if han is not None:
                if han > time.time():
                    return {"id": 0, "username": ADMIN, "vai": "shop"}
                del self._phien_admin[b]
                return None
        p = self.kho.doc_phien(b)
        if not p or p["het_han"] <= time.time():
            return None
        return {"id": p["tai_khoan_id"], "username": p["username"], "vai": p["vai"]}

    def xoa_phien(self, token) -> None:
        if not token:
            return
        b = bam_token(str(token))
        with self._khoa:
            self._phien_admin.pop(b, None)
        self.kho.xoa_phien(b)
