# Thiết kế: CP4 · chi phí khi dùng thật (guide 4.2) + bản nháp slide (guide 5.1)

Nhánh `feature/cp4-chi-phi` (worktree riêng), PR vào `develop`. Hạn: CP4 14:30 Thứ Bảy 28/11.

## Vì sao

CP4 đòi "chi phí / task thành công ở kịch bản cơ sở, kèm tên model" và slide (điều kiện cứng số 4 của rubric). Lượt 2 đã chốt sau PR #46 (`run-5@20261128-021955`, 28/30, 93%, đạt chuẩn), còn `cost/` và slide vẫn là khung trống, chưa ai làm. Hai phần này nối nhau: slide trang 6–7 lấy số từ `cost/cost-estimate.md`.

## Mục tiêu

1. `cost/personas.yaml` có nguồn cho mọi số: 3 kiểu shop từ phỏng vấn P1–P4, số người dùng ở quy mô thật từ nguồn công khai, giá ≥2 mức model.
2. Một lượt `python run.py simulate --rate-from eval/run-5.csv` (50 phiên, seed 42) trên `develop` đã có #46 → `cost/simulate-1.csv` + `-summary.md` + `traces/simulate-1.jsonl`.
3. `cost/cost-estimate.md` điền đủ §1–§3 (và §4 độ nhạy ngắn), `spec.md` §8 điền, §10 thêm dòng.
4. Bản nháp slide 8 trang theo `slides/outline.md`, mỗi trang ≥1 số có nguồn, xuất `demo-slides.pdf` ở gốc repo.

## Không làm

- Không đụng `eval/` (lượt, report, README) hay `codebase/`. Số đánh giá trên slide chép từ `eval/report.md` như đang có.
- Không làm 4.3 người dùng thử (cần người thật), không viết spec §9 (Việt Anh giữ), không viết `reflection/`.
- Không chọn thay nhóm go / iterate / stop: trang 7 ghi đề xuất có số, nhóm chốt.

## Phải tránh

- Bịa số: số nào không có nguồn thì ghi *(tự ước tính)* kèm cách ước.
- Sửa `simulate-1.*` sau khi chạy. Chạy lại thì thành `simulate-2`.
- Slide nói "đạt" hay "đáng làm" mà không dẫn số.

## Ràng buộc

- `cost/simulate.py`, `run.py` là khung, không sửa.
- §8 là phần của Hưng (kế hoạch CP3): PR cần Hưng duyệt.
- Lượt mô phỏng gọi model thật (Sonnet 5.5, ≈ 113 lần gọi, ≈ $0.5), dùng `.env` của nhóm, không commit `.env`.
- Commit / PR không có dòng ghi công AI (`AGENTS.md`).

## Đầu vào đã chốt

- **Persona** (spec §2, phỏng vấn câu 2 và câu 4): `shop_nho` (P4, 260 đơn / tháng, 2 lượt / phiên, share 0,25) · `shop_vua` (P1, P3, 400 đơn, 3 lượt, 0,5) · `shop_lon` (P2, 650 đơn, 1 lượt, 0,25). Lượt / phiên = 1 + số lần hỏi lại, quy đổi từ số lượt nhắn như ghi chú cũ trong `personas.yaml`, làm tròn lên. Share theo tỉ lệ trong 4 shop *(tự ước tính)*.
- **Số người dùng:** cơ sở 11.606 = người nộp thuế kinh doanh TMĐT Cục Thuế TP.HCM đưa vào quản lý đến hết 10/2024 ([Thanh Niên 04/12/2024](https://thanhnien.vn/doanh-nghiep-ca-nhan-kinh-doanh-thuong-mai-dien-tu-can-luu-y-thue-185241203172338583.htm)); thấp 1.161 (10% dùng) và cao 23.212 (gấp đôi, tính người bán chưa đăng ký thuế) đều *(tự ước tính)*. Ghi rõ bài báo không tách người bán qua mạng xã hội.
- **Giá** (`further-reading/model-prices.md` của repo đề, BTC xem 25/11/2026): Haiku 5.5 0,10 / 0,50 · Sonnet 5.5 2,00 / 10,00 · Opus 5.5 4,00 / 20,00 USD / 1M token. Token đo trên Sonnet 5.5 (model nhóm chạy), ghi "đo trên Sonnet, tính giá Haiku / Opus".
- **Tỷ giá:** để trống trong `personas.yaml`; trong `cost-estimate.md` §3 quy đổi tay bằng một tỷ giá có link + ngày xem để so với impact VND.

## Cách làm

**Chi phí:** chọn cách *nộp số từ một lượt duy nhất chạy trên code đã merge #46*. Cách khác đã cân nhắc: commit số tạm từ `run-2` trước khi #46 xong (bỏ: lượt đó ứng với code cũ và không được sửa). Lượt chạy thử lúc trước (trên nhánh của An, trước khi sửa) bỏ đi, không commit.

**Slide** (quyết định của Claude, nhóm có thể đổi):

| Cách | Được | Mất |
|---|---|---|
| **Chọn — deck HTML trong repo** `slides/demo-slides.html`, xuất `demo-slides.pdf` bằng headless Chromium (`npx playwright`, tải ≈150MB trên máy này, không thêm vào repo) | Đổi số → sửa và xuất lại một lệnh; cả nhóm sửa qua PR | Trông giản dị hơn; người không quen HTML khó sửa |
| Deck trên claude.ai (loại Slides) | Đẹp, tải PDF / PPTX | Mỗi lần đổi số phải tải tay rồi commit; chỉ người có link sửa |

Một file HTML tự chứa (không CDN), mỗi trang một `<section>` khổ 16:9, in ra PDF mỗi `<section>` một trang. Trang 4 (demo) ghi 1 câu thường + 1 câu khó lấy từ `eval/benchmark.csv` kèm output thật trong `eval/run-5.csv`. Bảng "Ai nói trang nào" trong `outline.md` để trống cho nhóm.

## Kết luận dự kiến cần thể hiện (từ lượt chạy thử, số thật lấy từ lượt nộp)

Lượt thử cho thấy Sonnet 5.5 ≈ $4 / shop / tháng (≈ 100.000đ), ngang hoặc vượt phần phí ship tiết kiệm được / shop (≈ 49.000–123.000đ theo §2), còn Haiku 5.5 rẻ hơn ≈ 20 lần. `cost-estimate.md` §3 và slide trang 7 nêu đúng điều này: đáng làm nếu chạy được trên model rẻ; việc tiếp theo là chạy lại eval trên Haiku để biết tỉ lệ đạt (trang 8).

## Để người làm tự quyết

Bố cục, màu chữ của slide; câu chữ trong `cost-estimate.md` §4; chọn câu khó nào cho trang 4 (ưu tiên câu quy đổi địa chỉ cũ).
