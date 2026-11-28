# Thiết kế: CP4 · chi phí khi dùng thật (guide 4.2) + bản nháp slide (guide 5.1)

Nhánh `feature/cp4-chi-phi` (worktree riêng), PR vào `develop`. Hạn: CP4 14:30 Thứ Bảy 28/11.

## Vì sao

CP4 đòi "chi phí / task thành công ở kịch bản cơ sở, kèm tên model" và slide (điều kiện cứng số 4 của rubric). Lượt 2 đã chốt sau PR #46 (`run-5@20261128-021955`, 28/30, 93%, đạt chuẩn), còn `cost/` và slide vẫn là khung trống, chưa ai làm. Hai phần này nối nhau: slide trang 6–7 lấy số từ `cost/cost-estimate.md`.

## Mục tiêu

1. `cost/personas.yaml` có nguồn cho mọi số: 3 kiểu shop từ phỏng vấn P1–P4, số người dùng tách thành quy mô tham chiếu có nguồn × các tỉ lệ *(tự ước tính)*, giá ≥2 mức model.
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
- Lượt mô phỏng gọi model thật (Sonnet 5.5, ≈ 113 lần gọi, ≈ $0.5), không commit `.env`. `codebase/ai.py` đọc `.env` ở gốc **bản checkout đang chạy** (worktree này, không phải repo chính) và thiếu cấu hình thì lặng lẽ chạy `fake`. Vì vậy trước lượt nộp phải xác nhận lượt thử ghi model `claude-sonnet-5-5` và token > 0 (xem kế hoạch Task 1).
- Commit / PR không có dòng ghi công AI (`AGENTS.md`).

## Đầu vào đã chốt

- **Persona** (spec §2, phỏng vấn câu 2 và câu 4): `shop_nho` (P4, 260 đơn / tháng, 2 lượt / phiên, share 0,25) · `shop_vua` (P1, P3, 400 đơn, 3 lượt, 0,5) · `shop_lon` (P2, 650 đơn, 1 lượt, 0,25). Lượt / phiên = 1 + số lần hỏi lại, quy đổi từ số lượt nhắn như ghi chú cũ trong `personas.yaml`, làm tròn lên. Share theo tỉ lệ trong 4 shop *(tự ước tính)*.
- **Số người dùng** = quy mô tham chiếu × hệ số phủ × tỉ lệ thuộc lát cắt × tỉ lệ sử dụng. `simulate.py` nhân thẳng số này vào chi phí tháng, nên mỗi thừa số phải ghi rõ:

  | Thừa số | Thấp | Cơ sở | Cao | Nguồn |
  |---|---:|---:|---:|---|
  | Quy mô tham chiếu: người nộp thuế kinh doanh TMĐT Cục Thuế TP.HCM đưa vào quản lý, luỹ kế đến hết 10/2024 | 11.606 | 11.606 | 11.606 | [Thanh Niên 04/12/2024](https://thanhnien.vn/doanh-nghiep-ca-nhan-kinh-doanh-thuong-mai-dien-tu-can-luu-y-thue-185241203172338583.htm) |
  | Hệ số phủ: thêm người bán chưa đăng ký thuế | 1 | 1 | 2 | *(tự ước tính)* |
  | Tỉ lệ thuộc lát cắt: tự chốt đơn qua tin nhắn rồi tạo vận đơn (spec §1) | 0,5 | 0,5 | 0,5 | *(tự ước tính)*: bài báo không tách người bán qua mạng xã hội |
  | Tỉ lệ sử dụng: shop thuộc lát cắt dùng công cụ | 0,1 | 0,3 | 0,5 | *(tự ước tính)* |
  | **Số người dùng** (làm tròn) | **580** | **1.741** | **5.803** | tích các dòng trên |

  Cả ba kịch bản, kể cả cơ sở, đều dựa trên tỉ lệ chưa đo. Ba thừa số *(tự ước tính)* là đề xuất, **nhóm chốt trước lượt nộp** (Task 1 Step 3); đổi thừa số thì chỉ đổi `users` trong `personas.yaml`. `cost-estimate.md` §1 và slide ghi nguyên bảng này, không ghi "11.606 người dùng".
- **Giá** (`further-reading/model-prices.md` của repo đề, BTC xem 25/11/2026): Haiku 5.5 0,10 / 0,50 · Sonnet 5.5 2,00 / 10,00 · Opus 5.5 4,00 / 20,00 USD / 1M token. Token đo trên Sonnet 5.5 (model nhóm chạy), ghi "đo trên Sonnet, tính giá Haiku / Opus".
- **Tỷ giá:** để trống trong `personas.yaml`; trong `cost-estimate.md` §3 quy đổi tay bằng một tỷ giá có link + ngày xem để so với impact VND.

## Cách làm

**Chi phí:** chọn cách *nộp số từ một lượt duy nhất chạy trên code đã merge #46*. Cách khác đã cân nhắc: commit số tạm từ `run-2` trước khi #46 xong (bỏ: lượt đó ứng với code cũ và không được sửa). Lượt chạy thử lúc trước (trên nhánh của An, trước khi sửa) bỏ đi, không commit.

**Slide** (quyết định của Claude, nhóm có thể đổi):

| Cách | Được | Mất |
|---|---|---|
| **Chọn — deck HTML trong repo** `slides/demo-slides.html`, xuất `demo-slides.pdf` bằng headless Chromium (`npx playwright`, tải ≈150MB trên máy này, không thêm vào repo) | Đổi số → sửa và xuất lại một lệnh; cả nhóm sửa qua PR | Trông giản dị hơn; người không quen HTML khó sửa |
| Deck trên claude.ai (loại Slides) | Đẹp, tải PDF / PPTX | Mỗi lần đổi số phải tải tay rồi commit; chỉ người có link sửa |

Một file HTML tự chứa (không CDN), mỗi trang một `<section>` khổ 16:9, in ra PDF mỗi `<section>` một trang. Trang 4 (demo) ghi 1 câu thường + 1 câu khó lấy từ `eval/benchmark.csv` kèm output thật trong `eval/run-5.csv`. Phân công người nói theo bảng trong `slides/outline.md`.

## Cách kết luận: so chi phí với ngưỡng hoà vốn (số thật lấy từ lượt nộp)

Spec §2 đo **phần đang mất**: ≈ 49.000–124.000đ phí ship / shop / tháng vì chép sai (đầu trên *(tự ước tính)*) và ≈ 214 phút / shop / tháng đổi địa chỉ cũ. Nhóm **chưa đo** AI tránh được bao nhiêu phần trong đó, nên không viết "tiết kiệm được 49.000–124.000đ".

`cost-estimate.md` §3 và slide trang 7 trình bày theo ngưỡng hoà vốn thay vì kết luận sẵn:

- Với mỗi model, chi phí / shop / tháng (cơ sở) = C, lấy từ `simulate-1-summary.md`, quy ra VND bằng tỷ giá có link + ngày xem.
- **Tỉ lệ phí ship phải tránh để hoà vốn** f\* = C ÷ phí ship đang mất, tính ở cả đầu dưới (49.000đ) và đầu trên (124.000đ). f\* > 100% nghĩa là riêng phí ship không đủ bù, kể cả tránh hết lỗi.
  - Ví dụ minh hoạ từ lượt chạy thử (không phải số nộp): C ≈ 100.000đ → f\* ≈ 81% ở đầu trên, > 100% ở đầu dưới.
- 214 phút / shop / tháng ghi riêng là thời gian **đang mất**, chưa quy ra tiền và chưa đo phần AI giảm được.
- Kết luận ghi dạng có điều kiện, phụ thuộc ba thứ: số mô phỏng (C), tỉ lệ lỗi AI tránh được (chưa đo) và tỉ lệ đạt eval của model rẻ (chưa chạy). Ví dụ: "Với Sonnet cần tránh ≥ X% phí ship mới hoà vốn; với Haiku cần ≥ Y%, nếu Haiku đạt tỉ lệ như Sonnet." Go / iterate / stop vẫn do nhóm chốt.
- **Hai giả định của dòng Haiku / Opus**, ghi trên cả `cost-estimate.md` và slide: (1) token đo trên Sonnet 5.5, chỉ đổi đơn giá; (2) cột "chi phí / task thành công" dùng tỉ lệ đạt 28/30 của Sonnet (`run-5`). Việc tiếp theo (trang 8): chạy eval trên Haiku để thay giả định (2) bằng số đo.

## Để người làm tự quyết

Bố cục, màu chữ của slide; câu chữ trong `cost-estimate.md` §4; chọn câu khó nào cho trang 4 (ưu tiên câu quy đổi địa chỉ cũ).
