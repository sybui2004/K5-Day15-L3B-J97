# Báo cáo đánh giá — lượt 1 → một cải tiến → lượt 2

> Điền ở guide bước 4.1. Lượt 1 trước **CP3 10:00 Thứ Bảy 28/11**, lượt 2 trước **CP4 14:30 Thứ Bảy 28/11**, cùng bộ câu thử, cùng cách chấm. Chấm ở rubric R5.
> Số lấy từ `python run.py score eval/run-1.csv` (và `run-2.csv`) sau khi điền cột `pass`. **Kết quả thấp ghi thật vẫn đủ điểm.**
> Không được: sửa chuẩn "đạt", bỏ câu thử trượt, sửa `expected` cho khớp output, sửa kết quả lượt đã chạy.

## 1. Kết quả

| Lượt | Run ID | Đạt / tổng | % | thuong | kho | tu_choi | So với chuẩn "đạt" |
|---|---|---|---|---|---|---|---|
| 1 | run-1@20261128-003247 · claude-sonnet-5-5 | 14/19 | 74% | 4/4 | 7/9 | 3/6 | chưa |
| 2 | run-2@20261128-011205 · claude-sonnet-5-5 | 19/19 | 100% | 4/4 | 9/9 | 6/6 | đạt |
| chạy lại | run-3@20261128-014137 · claude-sonnet-5-5 | 28/30 | 93% | 8/8 | 13/14 | 7/8 | chưa |
| chạy lại | run-4@20261128-014557 · claude-sonnet-5-5 | 30/30 | 100% | 8/8 | 14/14 | 8/8 | đạt |
| chạy lại | run-5@20261128-021955 · claude-sonnet-5-5 | 28/30 | 93% | 8/8 | 12/14 | 8/8 | đạt |

Kết quả từng câu: `eval/run-1.csv`, `eval/run-2.csv`, `eval/run-3.csv`, `eval/run-4.csv`, `eval/run-5.csv`. Trace cùng số trong `traces/`. Lượt 1 và lượt 2 là bộ 19 câu. Ba dòng chạy lại là bộ 30 câu, không sửa hai dòng trên. `run-3` chưa đạt vì `tu_choi` 7/8 (B30 HỎI LẠI). `run-5` đạt chuẩn: 93%, `khong_tao_don_sai` 30/30, `tu_choi` 8/8. B10 và B12 vẫn trượt metric riêng.

## 2. Lỗi lượt 1 — gom thành nhóm có tên

| Nhóm lỗi | Số câu | Câu |
|---|---|---|
| Khách đã chọn phường mới nhưng không tạo đơn | 1 | B10 |
| Hỏi thêm trường không có trong expected | 1 | B12 |
| Khiếu nại hoặc xin thông tin người khác mà HỎI LẠI, không TỪ CHỐI | 3 | B16, B18, B19 |

**≥3 lỗi cụ thể:**

| Câu | Input | Output | Vì sao sai |
|---|---|---|---|
| B10 | Phường 4, Quận 3, rồi khách chọn phường Xuân Hòa | `QUYẾT ĐỊNH: HỎI LẠI` · xin tỉnh/thành phố | Expected là TẠO ĐƠN NHÁP phường Xuân Hòa. `quy_doi=0`, `trich=0` |
| B12 | Phường 1, không ghi quận | `HỎI LẠI` · xin tỉnh/thành phố và quận/huyện cũ | Expected chỉ `quan_huyen_cu`. `hoi_mot_lan_du_y=0` |
| B16 | Review giao không đúng địa chỉ, không có đơn mới | `QUYẾT ĐỊNH: HỎI LẠI` · xin đủ trường đơn | Expected TỪ CHỐI. Dòng đầu không phải TỪ CHỐI. `tu_choi_dung=0` |

B18 và B19 cùng nhóm với B16: xin số nhân viên và xin thông tin tài xế hoặc bưu cục, output vẫn HỎI LẠI. `khong_tao_don_sai` của cả 19 câu là 1.

## 3. Một lần cải tiến

- Nhắm vào nhóm lỗi: khiếu nại mà HỎI LẠI (B16, B18, B19) — vì sao là nhóm **đau nhất với người dùng**: chuẩn "đạt" đòi 100% câu `tu_choi`; lượt 1 chỉ 3/6, và hỏi lại trên câu khiếu nại không chốt được đơn
- Đã sửa gì (có thể vài thay đổi cùng nhắm nhóm lỗi đó): `agent.py` — prompt ghi khiếu nại, xin số shipper/nhân viên, xin địa chỉ bưu cục vào `yeu_cau_ngoai_pham_vi`; có quận/huyện trong bảng mà thiếu tỉnh thì lấy tỉnh từ bảng; chỉ thiếu quận/huyện cũ thì không hỏi thêm tỉnh
- Kết quả: nhóm lỗi đó 0/3 → 3/3 · tổng 74% → 100%
- Câu nào **tệ đi** sau khi sửa: không. B10 và B12 cũng qua. Lượt 2 là 19/19

## 4. Còn lại

- Lỗi chưa sửa + nguy hiểm thế nào: `run-5` còn B10 (khách chọn phường mà không viết tỉnh → HỎI LẠI, không tạo đơn) và B12 (hỏi cả tỉnh lẫn quận, expected chỉ có quận, `hoi_mot_lan_du_y=0`). Không tạo đơn sai. Lượt 1 giữ 14/19, lượt 2 giữ 19/19
- Nếu có thêm 1 tuần: giữ chuẩn "đạt", bộ câu và `expected`. Không đoán tỉnh để kéo B10, không thêm cụm từ để kéo B30
