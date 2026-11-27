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

## Ngoài phạm vi (đợt sau, khi #45 đã merge)
- Tách giao diện ra `static/` và thiết kế lại (design-taste-frontend): nút "+ Hội thoại mới", khung "AI đã làm gì", "Vì sao hỏi lại", chi phí phiên, tab Nhật ký, hộp thư cuộn riêng.
- Khôi phục hội thoại tạo mới sau khi khởi động lại.

## Cách làm đã chọn
B (tách `static/`), làm thành 2 đợt: máy chủ trước, giao diện sau #45. Phương án A (giữ một file) bị loại theo lựa chọn của nhóm.
