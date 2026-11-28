"""Nơi lưu nhật ký của màn hình duyệt: nhật ký duyệt/huỷ và các lần chạy AI (trace, token, chi phí).

- Có DATABASE_URL (trong .env hoặc biến môi trường) → Postgres, cần `python -m pip install "psycopg[binary]"`.
- Không có → ghi file .jsonl trong data/ như trước (bản chạy thử không cần Postgres).

    kho = mo_kho()                      # chọn theo DATABASE_URL
    kho.ghi_duyet(dong)                 # {"ma_hoi_thoai", "quyet_dinh_ai", "truong_da_sua", "so_luot_hoi_lai", "ket_qua", "luc"}
    kho.ghi_lan_chay(dong)              # {"ma_hoi_thoai", "nguon", "quyet_dinh", "trace", "luc"}
    kho.doc_nhat_ky(gioi_han)           # {"duyet": [...], "lan_chay": [...]}, mới nhất trước

Ghi lỗi thì ném LoiKho (là OSError): người gọi quyết định chặn hay chỉ cảnh báo.
"""
import copy
import json
import os
import re
import threading
import time

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NHAT_KY = os.path.join(GOC, "data", "nhat-ky-duyet.jsonl")
LAN_CHAY = os.path.join(GOC, "data", "lan-chay-web.jsonl")
CHAT = os.path.join(GOC, "data", "chat-khach.json")  # tài khoản, phiên, tin chat khi chạy không có Postgres

BANG = """
CREATE TABLE IF NOT EXISTS nhat_ky_duyet (
    id              bigserial PRIMARY KEY,
    ma_hoi_thoai    text        NOT NULL,
    quyet_dinh_ai   text,
    truong_da_sua   jsonb       NOT NULL DEFAULT '[]',
    so_luot_hoi_lai integer     NOT NULL DEFAULT 0,
    ket_qua         text        NOT NULL,
    luc             timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS lan_chay (
    id           bigserial PRIMARY KEY,
    ma_hoi_thoai text        NOT NULL,
    nguon        text        NOT NULL,
    quyet_dinh   text,
    trace        jsonb       NOT NULL,
    luc          timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS tai_khoan (
    id           bigserial PRIMARY KEY,
    username     text        NOT NULL UNIQUE,
    mat_khau_bam text        NOT NULL,
    vai          text        NOT NULL,
    ip_tao       text,
    tao_luc      timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS phien_dang_nhap (
    token_bam    text PRIMARY KEY,
    tai_khoan_id bigint NOT NULL REFERENCES tai_khoan(id) ON DELETE CASCADE,
    het_han      double precision NOT NULL
);
CREATE TABLE IF NOT EXISTS tin_nhan (
    id           bigserial PRIMARY KEY,
    tai_khoan_id bigint NOT NULL REFERENCES tai_khoan(id) ON DELETE CASCADE,
    nguoi_noi    text        NOT NULL,
    noi_dung     text        NOT NULL,
    luc          timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS tin_nhan_tk ON tin_nhan (tai_khoan_id, id);
CREATE TABLE IF NOT EXISTS cuoc_chat (
    tai_khoan_id    bigint PRIMARY KEY REFERENCES tai_khoan(id) ON DELETE CASCADE,
    che_do          text    NOT NULL DEFAULT 'bot',
    trang_thai      text    NOT NULL DEFAULT 'cho_khach',
    phien_ban       integer NOT NULL DEFAULT 1,
    kq              jsonb,
    ma_don          text,
    ma_van_don      text,
    co_tin_chua_doc boolean NOT NULL DEFAULT false,
    moc_tin_id      bigint  NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS don_cu (
    id           bigserial PRIMARY KEY,
    tai_khoan_id bigint NOT NULL REFERENCES tai_khoan(id) ON DELETE CASCADE,
    moc_tin_id   bigint NOT NULL,
    ket_qua      text   NOT NULL,
    ma_don       text,
    truong       jsonb,
    luc          text
);
"""

CHAT_COT = ("che_do", "trang_thai", "phien_ban", "kq", "ma_don", "ma_van_don", "co_tin_chua_doc", "moc_tin_id")


class LoiKho(OSError):
    """Không ghi / đọc được nhật ký."""


class TrungTen(ValueError):
    """Username đã có người dùng."""


def _ghi_jsonl(path, dong):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(dong, ensure_ascii=False) + "\n")


def _doc_jsonl(path, gioi_han):
    if not os.path.exists(path):
        return []
    ra = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                ra.append(json.loads(line))
            except ValueError:
                continue  # dòng hỏng không làm hỏng cả nhật ký
    return ra[::-1][:gioi_han]


class KhoFile:
    ten = "file"

    def __init__(self, nhat_ky=NHAT_KY, lan_chay=None, chat=None):
        self.nhat_ky = nhat_ky
        self.lan_chay = lan_chay or os.path.join(os.path.dirname(nhat_ky), "lan-chay-web.jsonl")
        self.chat = chat or os.path.join(os.path.dirname(nhat_ky), "chat-khach.json")
        self._khoa_chat = threading.Lock()
        self._c = {"tai_khoan": [], "phien": {}, "tin": [], "cuoc_chat": {}, "don_cu": []}
        if os.path.exists(self.chat):
            try:
                with open(self.chat, encoding="utf-8") as f:
                    self._c.update(json.load(f))
            except (OSError, ValueError) as e:
                raise LoiKho("không đọc được %s: %s" % (self.chat, e))

    # ---- chat khách: một file JSON, ghi lại cả file sau mỗi thay đổi (bản demo chạy máy, dữ liệu nhỏ) ----
    def _luu_chat(self):
        os.makedirs(os.path.dirname(self.chat), exist_ok=True)
        tam = self.chat + ".tmp"
        with open(tam, "w", encoding="utf-8") as f:
            json.dump(self._c, f, ensure_ascii=False)
        os.replace(tam, self.chat)

    def _tk_theo_id(self, i):
        return next((t for t in self._c["tai_khoan"] if t["id"] == i), None)

    def tao_tai_khoan(self, username, mat_khau_bam, vai, ip):
        with self._khoa_chat:
            if any(t["username"] == username for t in self._c["tai_khoan"]):
                raise TrungTen(username)
            i = max((t["id"] for t in self._c["tai_khoan"]), default=0) + 1
            self._c["tai_khoan"].append({"id": i, "username": username, "mat_khau_bam": mat_khau_bam, "vai": vai,
                                         "ip_tao": ip, "tao_luc": time.strftime("%Y-%m-%dT%H:%M:%S")})
            self._luu_chat()
            return i

    def tim_tai_khoan(self, username):
        with self._khoa_chat:
            t = next((t for t in self._c["tai_khoan"] if t["username"] == username), None)
            return {k: t[k] for k in ("id", "username", "mat_khau_bam", "vai")} if t else None

    def luu_phien(self, token_bam, tai_khoan_id, het_han):
        with self._khoa_chat:
            self._c["phien"][token_bam] = {"tai_khoan_id": tai_khoan_id, "het_han": het_han}
            self._luu_chat()

    def doc_phien(self, token_bam):
        with self._khoa_chat:
            p = self._c["phien"].get(token_bam)
            t = self._tk_theo_id(p["tai_khoan_id"]) if p else None
            return {"tai_khoan_id": t["id"], "username": t["username"], "vai": t["vai"],
                    "het_han": p["het_han"]} if t else None

    def xoa_phien(self, token_bam):
        with self._khoa_chat:
            if self._c["phien"].pop(token_bam, None) is not None:
                self._luu_chat()

    def ghi_tin(self, tai_khoan_id, nguoi_noi, noi_dung):
        with self._khoa_chat:
            i = max((t["id"] for t in self._c["tin"]), default=0) + 1
            tin = {"id": i, "tai_khoan_id": tai_khoan_id, "nguoi_noi": nguoi_noi, "noi_dung": noi_dung,
                   "luc": time.strftime("%Y-%m-%dT%H:%M:%S")}
            self._c["tin"].append(tin)
            self._luu_chat()
            return dict(tin)

    def doc_tin(self, tai_khoan_id, sau_id=0):
        with self._khoa_chat:
            return [dict(t) for t in self._c["tin"] if t["tai_khoan_id"] == tai_khoan_id and t["id"] > sau_id]

    def luu_cuoc_chat(self, tai_khoan_id, d):
        with self._khoa_chat:
            self._c["cuoc_chat"][str(tai_khoan_id)] = {k: copy.deepcopy(d.get(k)) for k in CHAT_COT}
            self._luu_chat()

    def doc_cac_cuoc_chat(self):
        with self._khoa_chat:
            ra = []
            for k, d in self._c["cuoc_chat"].items():
                t = self._tk_theo_id(int(k))
                if t:
                    ra.append(dict(copy.deepcopy(d), tai_khoan_id=t["id"], username=t["username"]))
            return ra

    def ghi_don_cu(self, tai_khoan_id, d):
        with self._khoa_chat:
            self._c["don_cu"].append(dict(copy.deepcopy(d), tai_khoan_id=tai_khoan_id))
            self._luu_chat()

    def doc_don_cu(self, tai_khoan_id):
        with self._khoa_chat:
            return [copy.deepcopy(d) for d in self._c["don_cu"] if d["tai_khoan_id"] == tai_khoan_id]

    def ghi_duyet(self, dong):
        _ghi_jsonl(self.nhat_ky, dong)

    def ghi_lan_chay(self, dong):
        _ghi_jsonl(self.lan_chay, dong)

    def doc_nhat_ky(self, gioi_han=100):
        return {"duyet": _doc_jsonl(self.nhat_ky, gioi_han), "lan_chay": _doc_jsonl(self.lan_chay, gioi_han)}


def _gan_mui_gio(luc):
    """'2026-11-27T10:00:00' (giờ máy) → kèm offset của máy, để Postgres không hiểu nhầm là UTC."""
    if luc and not re.search(r"(Z|[+-]\d{2}:?\d{2})$", luc):
        return luc + time.strftime("%z")
    return luc


def _gio_may(dt):
    """timestamptz đọc từ Postgres → chuỗi giờ máy, cùng dạng với nhật ký file."""
    return dt.astimezone().strftime("%Y-%m-%dT%H:%M:%S") if dt else None


class KhoPostgres:
    """Mỗi thao tác một kết nối ngắn: máy chủ web chạy một luồng, lượng ghi nhỏ."""
    ten = "postgres"

    def __init__(self, url):
        try:
            import psycopg
        except ImportError:
            raise LoiKho('có DATABASE_URL nhưng chưa cài psycopg: python -m pip install "psycopg[binary]"')
        self._psycopg = psycopg
        self.url = url
        self._chay(lambda cur: cur.execute(BANG))

    def _chay(self, viec):
        try:
            with self._psycopg.connect(self.url, connect_timeout=5) as conn:
                with conn.cursor() as cur:
                    return viec(cur)
        except self._psycopg.Error as e:
            raise LoiKho("Postgres: %s" % (str(e).strip().splitlines() or [type(e).__name__])[0])

    def ghi_duyet(self, d):
        self._chay(lambda cur: cur.execute(
            "INSERT INTO nhat_ky_duyet (ma_hoi_thoai, quyet_dinh_ai, truong_da_sua, so_luot_hoi_lai, ket_qua, luc)"
            " VALUES (%s, %s, %s::jsonb, %s, %s, COALESCE(%s::timestamptz, now()))",
            (d["ma_hoi_thoai"], d.get("quyet_dinh_ai"), json.dumps(d.get("truong_da_sua") or [], ensure_ascii=False),
             d.get("so_luot_hoi_lai") or 0, d["ket_qua"], _gan_mui_gio(d.get("luc")))))

    def ghi_lan_chay(self, d):
        self._chay(lambda cur: cur.execute(
            "INSERT INTO lan_chay (ma_hoi_thoai, nguon, quyet_dinh, trace, luc)"
            " VALUES (%s, %s, %s, %s::jsonb, COALESCE(%s::timestamptz, now()))",
            (d["ma_hoi_thoai"], d["nguon"], d.get("quyet_dinh"), json.dumps(d["trace"], ensure_ascii=False),
             _gan_mui_gio(d.get("luc")))))

    # ---- chat khách ----
    def tao_tai_khoan(self, username, mat_khau_bam, vai, ip):
        def viec(cur):
            cur.execute("INSERT INTO tai_khoan (username, mat_khau_bam, vai, ip_tao) VALUES (%s, %s, %s, %s)"
                        " ON CONFLICT (username) DO NOTHING RETURNING id", (username, mat_khau_bam, vai, ip))
            r = cur.fetchone()
            if r is None:
                raise TrungTen(username)
            return r[0]
        return self._chay(viec)

    def tim_tai_khoan(self, username):
        def viec(cur):
            cur.execute("SELECT id, username, mat_khau_bam, vai FROM tai_khoan WHERE username = %s", (username,))
            r = cur.fetchone()
            return dict(zip(("id", "username", "mat_khau_bam", "vai"), r)) if r else None
        return self._chay(viec)

    def luu_phien(self, token_bam, tai_khoan_id, het_han):
        self._chay(lambda cur: cur.execute(
            "INSERT INTO phien_dang_nhap (token_bam, tai_khoan_id, het_han) VALUES (%s, %s, %s)"
            " ON CONFLICT (token_bam) DO UPDATE SET het_han = EXCLUDED.het_han", (token_bam, tai_khoan_id, het_han)))

    def doc_phien(self, token_bam):
        def viec(cur):
            cur.execute("SELECT t.id, t.username, t.vai, p.het_han FROM phien_dang_nhap p JOIN tai_khoan t"
                        " ON t.id = p.tai_khoan_id WHERE p.token_bam = %s", (token_bam,))
            r = cur.fetchone()
            return dict(zip(("tai_khoan_id", "username", "vai", "het_han"), r)) if r else None
        return self._chay(viec)

    def xoa_phien(self, token_bam):
        self._chay(lambda cur: cur.execute("DELETE FROM phien_dang_nhap WHERE token_bam = %s", (token_bam,)))

    def ghi_tin(self, tai_khoan_id, nguoi_noi, noi_dung):
        def viec(cur):
            cur.execute("INSERT INTO tin_nhan (tai_khoan_id, nguoi_noi, noi_dung) VALUES (%s, %s, %s)"
                        " RETURNING id, luc", (tai_khoan_id, nguoi_noi, noi_dung))
            i, luc = cur.fetchone()
            return {"id": i, "tai_khoan_id": tai_khoan_id, "nguoi_noi": nguoi_noi, "noi_dung": noi_dung,
                    "luc": _gio_may(luc)}
        return self._chay(viec)

    def doc_tin(self, tai_khoan_id, sau_id=0):
        def viec(cur):
            cur.execute("SELECT id, nguoi_noi, noi_dung, luc FROM tin_nhan WHERE tai_khoan_id = %s AND id > %s"
                        " ORDER BY id", (tai_khoan_id, sau_id))
            return [{"id": r[0], "tai_khoan_id": tai_khoan_id, "nguoi_noi": r[1], "noi_dung": r[2],
                     "luc": _gio_may(r[3])} for r in cur.fetchall()]
        return self._chay(viec)

    def luu_cuoc_chat(self, tai_khoan_id, d):
        gia_tri = [d.get(k) for k in CHAT_COT]
        gia_tri[3] = json.dumps(gia_tri[3], ensure_ascii=False) if gia_tri[3] is not None else None
        self._chay(lambda cur: cur.execute(
            "INSERT INTO cuoc_chat (tai_khoan_id, %s) VALUES (%%s, %%s, %%s, %%s, %%s::jsonb, %%s, %%s, %%s, %%s)"
            " ON CONFLICT (tai_khoan_id) DO UPDATE SET %s" % (
                ", ".join(CHAT_COT), ", ".join("%s = EXCLUDED.%s" % (k, k) for k in CHAT_COT)),
            [tai_khoan_id] + gia_tri))

    def doc_cac_cuoc_chat(self):
        def viec(cur):
            cur.execute("SELECT c.tai_khoan_id, t.username, %s FROM cuoc_chat c JOIN tai_khoan t ON t.id = c.tai_khoan_id"
                        " ORDER BY c.tai_khoan_id" % ", ".join("c." + k for k in CHAT_COT))
            return [dict(zip(("tai_khoan_id", "username") + CHAT_COT, r)) for r in cur.fetchall()]
        return self._chay(viec)

    def ghi_don_cu(self, tai_khoan_id, d):
        self._chay(lambda cur: cur.execute(
            "INSERT INTO don_cu (tai_khoan_id, moc_tin_id, ket_qua, ma_don, truong, luc)"
            " VALUES (%s, %s, %s, %s, %s::jsonb, %s)",
            (tai_khoan_id, d.get("moc_tin_id") or 0, d.get("ket_qua"), d.get("ma_don"),
             json.dumps(d.get("truong"), ensure_ascii=False), d.get("luc"))))

    def doc_don_cu(self, tai_khoan_id):
        def viec(cur):
            cur.execute("SELECT moc_tin_id, ket_qua, ma_don, truong, luc FROM don_cu WHERE tai_khoan_id = %s ORDER BY id",
                        (tai_khoan_id,))
            return [dict(zip(("moc_tin_id", "ket_qua", "ma_don", "truong", "luc"), r)) for r in cur.fetchall()]
        return self._chay(viec)

    def doc_nhat_ky(self, gioi_han=100):
        def doc(cur):
            cur.execute("SELECT ma_hoi_thoai, quyet_dinh_ai, truong_da_sua, so_luot_hoi_lai, ket_qua, luc"
                        " FROM nhat_ky_duyet ORDER BY id DESC LIMIT %s", (gioi_han,))
            duyet = [dict(zip(("ma_hoi_thoai", "quyet_dinh_ai", "truong_da_sua", "so_luot_hoi_lai", "ket_qua"), r),
                          luc=_gio_may(r[5])) for r in cur.fetchall()]
            cur.execute("SELECT ma_hoi_thoai, nguon, quyet_dinh, trace, luc FROM lan_chay ORDER BY id DESC LIMIT %s",
                        (gioi_han,))
            lan = [dict(zip(("ma_hoi_thoai", "nguon", "quyet_dinh", "trace"), r), luc=_gio_may(r[4]))
                   for r in cur.fetchall()]
            return {"duyet": duyet, "lan_chay": lan}
        return self._chay(doc)


def mo_kho(nhat_ky=NHAT_KY):
    url = (os.environ.get("DATABASE_URL") or "").strip()
    return KhoPostgres(url) if url else KhoFile(nhat_ky)
