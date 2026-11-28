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

Lấy ngày **28/11/2026**: 100 review mới nhất của app GHN (`vn.ghn.app.giaohangnhanh`) trên Google Play, sắp "Mới nhất", mọi mức sao, ngôn ngữ vi, quốc gia vn (thư viện `google-play-scraper` 1.2.7, cùng nguồn dữ liệu trang Google Play dùng khi cuộn). Review viết từ 16/10 đến 26/11/2026. App lúc lấy: 12.137 lượt đánh giá, điểm 1,4. Không lưu tên người viết; mã đơn trong review thay bằng `[mã đơn]`. Không thêm app quản lý tin nhắn: phỏng vấn không nêu tên app nào.

Đã đọc cả 100 review trước khi gắn nhãn. Các *kiểu* chuyện thấy được:
- Chậm lấy hàng, chậm giao, hàng nằm kho nhiều ngày (nhiều nhất).
- Hoàn hàng hoặc không giao, ghi lý do "không liên lạc được người nhận" dù người nhận nói không có cuộc gọi nào.
- Nhầm thông tin đơn: dán nhầm mã vận đơn sang đơn người khác, tự ghi sai thông tin đơn, không tìm được nhà.
- App lỗi (đăng xuất, OTP, COD), giá và phí, mất hàng, bồi thường, thái độ shipper hoặc tổng đài.

## 3. Kết quả

Dữ liệu từng review: `evidence/review-ghn.csv` (cột `stt, so_sao, nhan, cau_dau`). Đếm: `python evidence/count_review.py`.

| Đếm gì | x / N | % | Ghi chú |
|---|---|---|---|
| `sai_thieu_thong_tin_nhan_hang` | 14/100 | 14% | (a) sai thông tin, nhầm đơn, nhầm người, không tìm được địa chỉ: 4 (stt 7, 47, 69, 89) · (b) hoàn / không giao vì "không liên lạc được người nhận": 10 (stt 5, 29, 39, 43, 48, 58, 62, 63, 92, 100) |
| `tra_loi_cham` | 1/100 | 1% | stt 6 ("Vô đợi gần 10p") |
| `khac` | 85/100 | 85% | chậm lấy / giao hàng, app lỗi, giá, mất hàng, thái độ |
| Nhắc địa chỉ sau sáp nhập / địa giới mới | 0/100 | 0% | tìm thêm theo từ khoá (sáp nhập, phường mới, địa giới, địa chỉ cũ/mới, phường, xã, quận): chỉ stt 22 có chữ "quận" ("quận đi quận về", nói về đường đi của hàng) |

**Hai người gắn nhãn 20 review đầu:** Claude Code gắn nhãn cả 100 review (20 review đầu: `khac` 17 · `sai_thieu_thong_tin_nhan_hang` 2 · `tra_loi_cham` 1). **Người thứ hai trong nhóm chưa gắn độc lập** 20 review này; khi gắn xong ghi kết quả khớp x/20 vào đây.

## 4. ≥5 ví dụ cụ thể (mã dòng / mã đã ẩn danh, không đoán ai là ai)

1. stt 47 (1 sao): "Khiếu nại đơn hàng [mã đơn] dán mvd của tôi vào 1 đơn hàng của người khác . tôi nhận sai hàng" — nhầm người nhận.
2. stt 89 (1 sao): "tự ghi thông tin đơn sai, không giao hàng cho khách mà lại báo giao hàng thành công" — sai thông tin đơn.
3. stt 7 (2 sao): "đến đơn thứ 2 t gửi cho bạn t, thì bên GHN dán lộn mã đơn của t" — nhầm đơn.
4. stt 69 (1 sao): "tại sao địa chỉ rõ ràng mà shiper lại không tìm thấy nhà." — không giao được vì địa chỉ.
5. stt 100 (1 sao): "không nhận được một cuộc gọi mà để cập nhật là không liên lạc được người nhận" — hoàn / không giao vì "không liên lạc được".
6. stt 92 (3 sao): "lấy lý do, không gọi được cho người nhận hàng, mà trong khi đó số điện thoại đang sử dụng bình thường" — như trên.

## 5. Giới hạn của data

Data cho biết người ta **làm gì**, không cho biết **vì sao**. Thiếu gì, lệch về phía nào: người viết review GHN phần lớn là người nhận hoặc người gửi lẻ phàn nàn về **khâu giao hàng của GHN**, không phải chủ shop kể chuyện chép thông tin từ chat. Lỗi chép sai ở phía shop thường không lộ ra trong review app vận chuyển, nên 14% là bằng chứng gián tiếp: thông tin nhận hàng sai hoặc "không liên lạc được" có làm đơn bị hoàn, nhưng không đo được phần do shop chép sai. Nhóm (b) có thể do shipper không gọi chứ không do sđt sai. 100 review trong 6 tuần, điểm app 1,4, nên lệch về phía phàn nàn. Không review nào nhắc địa chỉ sau sáp nhập, nên data này **không** kiểm được con số 20–45% đơn địa chỉ cũ ở phỏng vấn.
→ Kiểm lại bằng phỏng vấn / khảo sát nào: phỏng vấn P1–P4 (`evidence/interviews/`): 4/4 shop kể vụ chép sai trong 1 tháng qua và vụ hoàn vì không gọi được khách (P3 "nằm ở bưu cục 4 ngày không gọi được cho khách nên bị hoàn về"); khớp với nhóm (b). Địa chỉ cũ chỉ có nguồn phỏng vấn.
