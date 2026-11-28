"""Đếm nhãn trong evidence/review-ghn.csv (thay cho COUNTIF). Chạy: python evidence/count_review.py

Cột `nhac_dia_gioi_moi` (co / khong) gắn khi rà toàn văn từng review: review có nhắc địa chỉ sau
sáp nhập / địa giới mới hay không. CSV chỉ giữ câu đầu, nên cột này là cách kiểm lại kết quả đó.
"""
import collections, csv, os

duong = os.path.join(os.path.dirname(__file__), "review-ghn.csv")
dong = list(csv.DictReader(open(duong, encoding="utf-8")))
dem = collections.Counter(d["nhan"] for d in dong)
n = len(dong)
for nhan in ("sai_thieu_thong_tin_nhan_hang", "tra_loi_cham", "khac"):
    print("%-32s %3d/%d (%d%%)" % (nhan, dem[nhan], n, round(100 * dem[nhan] / n)))
co = sum(d["nhac_dia_gioi_moi"] == "co" for d in dong)
print("%-32s %3d/%d (%d%%)" % ("nhac_dia_gioi_moi = co", co, n, round(100 * co / n)))
dau = collections.Counter(d["nhan"] for d in dong[:20])
print("20 review đầu (để hai người gắn nhãn đối chiếu):", dict(dau))
