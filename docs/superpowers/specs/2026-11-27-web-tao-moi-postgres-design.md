# Màn hình duyệt: tạo hội thoại mới, trace + chi phí, nhật ký Postgres (phần máy chủ)

## Vì sao
Demo trước giám khảo (rubric R7): phải "chạy được câu thử lạ giám khảo đưa tại chỗ" và trả lời được "chi phí / task tính thế nào". Màn hình hiện chỉ có 10 hội thoại mẫu, không cho thấy AI đã làm gì và tốn bao nhiêu.

## Phạm vi đợt này (máy chủ)
- `POST /api/moi` `{ma_khach?, luot: [{vai: khach|shop, tin}]}` → ghép như hộp thư (`inbox._dung_text`), chạy `xu_ly`, thêm vào hộp thư với mã `HT-M01`, `HT-M02`…
- Mỗi lần chạy AI (tải hộp thư, tạo mới, khách trả lời) giữ `trace` trên phiên: các bước (model / công cụ / ghi chú), token, thời gian, chi phí USD (VND nếu có tỉ giá).
- `GET /api/hop-thu` thêm `tong` (tổng token, chi phí phiên demo) và `kho` (`postgres` | `file`).
- `GET /api/nhat-ky` → nhật ký duyệt/huỷ và các lần chạy, mới nhất trước.
- Lưu trữ `codebase/kho.py`: có `DATABASE_URL` thì ghi Postgres (`psycopg`), không có thì ghi file như cũ (`data/nhat-ky-duyet.jsonl`, `data/lan-chay-web.jsonl`).

## Ràng buộc
- `python run.py` vẫn chạy không cần Postgres (rubric: chạy theo README). `psycopg` chỉ import khi có `DATABASE_URL`.
- Chỉ sửa phần trên dòng `TRANG = ...` của `web.py`: PR #45 (Hưng) đang sửa HTML/CSS/JS, tránh xung đột.
- Giá model lấy từ `cost/personas.yaml`; model không có giá thì chỉ hiện token, ghi "chưa có giá" (không bịa số).
- Postgres ghi lỗi: thao tác Duyệt/Huỷ báo lỗi, không đổi trạng thái (giữ hành vi hiện tại). Ghi lần chạy lỗi: chỉ in cảnh báo, không chặn demo.

## Đợt 2 (sau khi #45 merge): giao diện `codebase/static/`
- `index.html`, `app.css`, `app.js`, `fonts/` (Manrope + JetBrains Mono có bộ chữ tiếng Việt, OFL, phục vụ cục bộ). `web.py` chỉ phục vụ file trong `static/` (`tep_tinh`), CSP chặt hơn: `style-src 'self'; font-src 'self'`.
- Ba cột, mỗi cột cuộn riêng (hộp thư không kéo cả trang); ≤1180px hai cột, ≤820px một cột.
- Nút *Hội thoại mới* → hộp thoại: mỗi dòng một tin (`Shop:` = shop), xem trước, 5 mẫu điền nhanh, đếm giây khi AI chạy.
- *AI đã làm gì*: từng bước model / công cụ từ trace, tóm tắt kết quả công cụ, token, thời gian, chi phí; *Vì sao AI chưa lên đơn* từ `kq.loi`; tổng phiên demo ở đầu trang; tab *Nhật ký*.
- Thiết kế theo design-taste-frontend phần dùng được cho công cụ nội bộ: bảng màu bốc `mint-pink-accounts` (lấy bảng thứ hai vì hồng đậm của bảng đầu trùng màu "Từ chối"), cặp chữ `manrope` (hai cặp đầu không có bộ chữ tiếng Việt), một cặp nút, hover/press theo motion.md, tắt chuyển động khi `prefers-reduced-motion`. Phần hero / landing page và cổng kiểm của skill không áp dụng.

## Ngoài phạm vi
- Khôi phục hội thoại tạo mới sau khi khởi động lại.

## Cách làm đã chọn
B (tách `static/`), làm thành 2 đợt: máy chủ trước, giao diện sau #45. Phương án A (giữ một file) bị loại theo lựa chọn của nhóm.
