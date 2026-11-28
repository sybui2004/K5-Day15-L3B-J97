"""Script đã dùng ngày 28/11/2026 để lấy 100 review mới nhất của app GHN trên Google Play.

Chạy: pip install --target <thu_muc_thu_vien> google-play-scraper==1.2.7
      python evidence/fetch_review.py <thu_muc_thu_vien> <file_ra.json>

File ra chứa toàn văn review (chưa che mã đơn): để ngoài repo, không commit.
Chạy lại vào ngày khác sẽ ra 100 review khác. Số đã công bố đếm từ evidence/review-ghn.csv.
"""
import sys, json
sys.path.insert(0, sys.argv[1])
from google_play_scraper import reviews, Sort, app

info = app('vn.ghn.app.giaohangnhanh', lang='vi', country='vn')
print('app:', info.get('title'), '| số đánh giá:', info.get('ratings'), '| điểm:', info.get('score'))
kq, _ = reviews('vn.ghn.app.giaohangnhanh', lang='vi', country='vn', sort=Sort.NEWEST, count=100)
# Chỉ giữ số sao, ngày, nội dung — không lưu tên người viết.
out = [{'stt': i + 1, 'so_sao': r['score'], 'ngay': r['at'].strftime('%Y-%m-%d'), 'noi_dung': r['content'] or ''}
       for i, r in enumerate(kq)]
json.dump(out, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print('lấy được', len(out), 'review ·', out[-1]['ngay'], '→', out[0]['ngay'])
