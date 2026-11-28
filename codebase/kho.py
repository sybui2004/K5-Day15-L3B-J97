"""Nơi lưu nhật ký của màn hình duyệt: nhật ký duyệt/huỷ và các lần chạy AI (trace, token, chi phí).

- Có DATABASE_URL (trong .env hoặc biến môi trường) → Postgres, cần `python -m pip install "psycopg[binary]"`.
- Không có → ghi file .jsonl trong data/ như trước (bản chạy thử không cần Postgres).

    kho = mo_kho()                      # chọn theo DATABASE_URL
    kho.ghi_duyet(dong)                 # {"ma_hoi_thoai", "quyet_dinh_ai", "truong_da_sua", "so_luot_hoi_lai", "ket_qua", "luc"}
    kho.ghi_lan_chay(dong)              # {"ma_hoi_thoai", "nguon", "quyet_dinh", "trace", "luc"}
    kho.doc_nhat_ky(gioi_han)           # {"duyet": [...], "lan_chay": [...]}, mới nhất trước

Ghi lỗi thì ném LoiKho (là OSError): người gọi quyết định chặn hay chỉ cảnh báo.
"""
import json
import os
import re
import time

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NHAT_KY = os.path.join(GOC, "data", "nhat-ky-duyet.jsonl")
LAN_CHAY = os.path.join(GOC, "data", "lan-chay-web.jsonl")

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
"""


class LoiKho(OSError):
    """Không ghi / đọc được nhật ký."""


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

    def __init__(self, nhat_ky=NHAT_KY, lan_chay=None):
        self.nhat_ky = nhat_ky
        self.lan_chay = lan_chay or os.path.join(os.path.dirname(nhat_ky), "lan-chay-web.jsonl")

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
