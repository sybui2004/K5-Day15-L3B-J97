# Đào data — cách đếm và kết quả

> Điền ở guide bước 1.2. Ôn lại: ngày 2, ngày 6 · lab ngày 2, lab ngày 6.
> Không đào data thì xoá file này. Script / công thức đếm để trong repo (vd `evidence/count.py` hoặc ghi công thức Sheets ngay dưới), người khác chạy lại phải ra cùng số.
> Repo chỉ chứa số đã tổng hợp và vài dòng ví dụ — không chép lại nguyên file data.

## 1. Cách đếm — viết TRƯỚC khi chạy

> Viết lúc 27/11, **trước khi đọc review đầu tiên**. Đây là nguồn kiểm chéo cho phỏng vấn, không phải nguồn chính.

- Data dùng: review trên Google Play của app **GHN** (Giao Hàng Nhanh); thêm app quản lý tin nhắn chủ shop đang dùng nếu phỏng vấn nêu tên. **100 review mới nhất** mỗi app tính đến ngày đếm, sắp theo "Mới nhất", **mọi mức sao**.
- Đếm gì: số review kể chuyện **sai hoặc thiếu thông tin nhận hàng** (sai địa chỉ, sai phường, sai sđt, giao nhầm người, hoàn hàng vì không liên lạc được). Đếm riêng số review **nhắc địa chỉ sau sáp nhập / địa giới mới**.
- Nhãn (mỗi review đúng một nhãn, gắn theo chuyện được kể chứ không theo số sao): `sai_thieu_thong_tin_nhan_hang` · `tra_loi_cham` · `khac` (giá, app lỗi, shipper thái độ…). Review vừa kể sai thông tin vừa kể chuyện khác thì gắn `sai_thieu_thong_tin_nhan_hang`.
- **Mẫu số là gì:** 100 review mới nhất của mỗi app (không lọc trước theo từ khoá, để không thổi phồng tỉ lệ). Review trống hoặc chỉ có emoji vẫn tính vào mẫu số, gắn `khac`.
- Cách làm lại được: ghi ngày đếm, chép mã hoặc 1 câu đầu của mỗi review vào `evidence/review-ghn.csv` (cột `stt, so_sao, nhan, cau_dau`, không ghi tên người viết), đếm bằng `COUNTIF` theo cột `nhan`. Hai người gắn nhãn độc lập 20 review đầu, lệch >4/20 thì viết lại định nghĩa nhãn trước khi gắn tiếp.

## 2. Đọc trước, đếm sau

Đã đọc __ dòng đầu và từ điển cột. Các *kiểu* hành vi thấy được (trước khi định nghĩa thứ cần đếm):
- __
- __

## 3. Kết quả

| Đếm gì | x / N | % | Ghi chú |
|---|---|---|---|
| | | | |
| | | | |

Ghi dạng "x/N (y%)". "Nhiều bạn…" không phải số.

## 4. ≥5 ví dụ cụ thể (mã dòng / mã đã ẩn danh, không đoán ai là ai)

1.
2.
3.
4.
5.

## 5. Giới hạn của data

Data cho biết người ta **làm gì**, không cho biết **vì sao**. Thiếu gì, lệch về phía nào: __
→ Kiểm lại bằng phỏng vấn / khảo sát nào: __
