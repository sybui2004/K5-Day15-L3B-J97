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

Dữ liệu từng review: `evidence/review-ghn.csv` (cột `stt, so_sao, nhan, nhac_dia_gioi_moi, cau_dau`). Đếm: `python evidence/count_review.py`.

| Đếm gì | x / N | % | Ghi chú |
|---|---|---|---|
| `sai_thieu_thong_tin_nhan_hang` | 7/100 | 7% | Nhầm mã vận đơn: STT 7, 47. Review nêu lý do giao không thành công là không liên lạc được hoặc khách không nghe máy: STT 5, 43, 63, 92, 100. |
| `tra_loi_cham` | 0/100 | 0% | stt 6 ("Vô đợi gần 10p") chuyển sang `khac` sau đối chiếu: không rõ đợi gì |
| `khac` | 93/100 | 93% | chậm lấy / giao hàng, app lỗi, giá, mất hàng, thái độ |
| Nhắc địa chỉ sau sáp nhập / địa giới mới | 0/100 | 0% | cột `nhac_dia_gioi_moi` trong `review-ghn.csv`, gắn khi rà toàn văn; script in tổng. Tìm thêm theo từ khoá trên toàn văn (sáp nhập, phường / xã mới, địa giới, địa chỉ cũ / mới, đơn vị hành chính): 0 review. stt 22 có chữ "quận" ("quận đi quận về", nói về đường đi của hàng); stt 12 "ko phải địa bàn của nó" không nói rõ do đổi địa giới nên ghi `khong` |

**Rà lại 14 nhãn ban đầu.** Đối chiếu toàn văn với định nghĩa ở mục 1 (Sỹ duyệt). Giữ 7 dòng trong bảng. Chuyển 7 dòng sang `khac`: STT 29, 39, 48, 58, 62 kể việc không gọi rồi hoàn hàng, không ghi lý do hoàn là không liên lạc được người nhận. STT 69 nói địa chỉ rõ nhưng shipper không tìm thấy nhà. STT 89 nói sai thông tin đơn nhưng không nêu trường nào sai. Kết quả phản ánh lời kể của người viết; lý do giao thất bại do bên vận chuyển ghi chưa chứng minh số điện thoại sai.

**Đối chiếu nhãn 20 review đầu:** bản nhãn ban đầu cho 100 review (công cụ hỗ trợ, khai ở `docs/ai-usage.md`) được đối chiếu với nhãn Sỹ gắn **độc lập** cho 20 review đầu (bản Sỹ dùng không kèm nhãn ban đầu, chỉ có số sao và câu đầu của mỗi review). Lệch 3/20 (đồng ý 85%), dưới ngưỡng 4/20 nên giữ định nghĩa nhãn. Đối chiếu toàn văn 3 dòng lệch: stt 5 và 7 giữ `sai_thieu_thong_tin_nhan_hang` (phần sau review kể "bảo không liên lạc được khách hàng" và "dán lộn mã đơn"; câu đầu không chứa chi tiết này); stt 6 chuyển sang `khac` vì không rõ đợi gì. 20 review đầu sau khi chốt: `khac` 18 · `sai_thieu_thong_tin_nhan_hang` 2. Sỹ duyệt toàn bộ nhãn cuối ngày 28/11.

## 4. ≥5 ví dụ cụ thể (mã dòng / mã đã ẩn danh, không đoán ai là ai)

1. stt 47 (1 sao): "Khiếu nại đơn hàng [mã đơn] dán mvd của tôi vào 1 đơn hàng của người khác . tôi nhận sai hàng" — nhầm mã vận đơn, nhận sai hàng.
2. stt 7 (2 sao): "đến đơn thứ 2 t gửi cho bạn t, thì bên GHN dán lộn mã đơn của t" — nhầm mã vận đơn.
3. stt 100 (1 sao): "không nhận được một cuộc gọi mà để cập nhật là không liên lạc được người nhận" — lý do giao thất bại: không liên lạc được.
4. stt 92 (3 sao): "lấy lý do, không gọi được cho người nhận hàng, mà trong khi đó số điện thoại đang sử dụng bình thường" — như trên.
5. stt 43 (1 sao): "Báo không liên hệ được nhưng chẳng có cuộc gọi nào từ shiper rồi tự hoàn hàng người ta về shop" — như trên.
6. stt 63 (1 sao): "hủy đơn báo ng gọi k nghe?" — lý do huỷ: khách không nghe máy.

Hai ví dụ ban đầu đã chuyển sang `khac` khi rà lại: stt 89 ("tự ghi thông tin đơn sai…", chưa rõ trường sai) và stt 69 ("địa chỉ rõ ràng mà shiper lại không tìm thấy nhà", người viết nói địa chỉ rõ).

## 5. Giới hạn của data

Data cho biết người ta **làm gì**, không cho biết **vì sao**. Thiếu gì, lệch về phía nào: người viết review GHN phần lớn là người nhận hoặc người gửi lẻ phàn nàn về **khâu giao hàng của GHN**, không phải chủ shop kể chuyện chép thông tin từ chat. Lỗi chép sai ở phía shop thường không lộ ra trong review app vận chuyển, nên 7% là bằng chứng gián tiếp: thông tin nhận hàng sai hoặc "không liên lạc được" có làm đơn bị hoàn, nhưng không đo được phần do shop chép sai. Lý do không liên lạc được có thể do shipper không gọi chứ không do sđt sai. 100 review trong 6 tuần, điểm app 1,4, nên lệch về phía phàn nàn. Không review nào nhắc địa chỉ sau sáp nhập, nên data này **không** kiểm được con số 20–45% đơn địa chỉ cũ ở phỏng vấn.
→ Kiểm lại bằng phỏng vấn / khảo sát nào: phỏng vấn P1–P4 (`evidence/interviews/`): 4/4 shop kể vụ chép sai trong 1 tháng qua và vụ hoàn vì không gọi được khách (P3 "nằm ở bưu cục 4 ngày không gọi được cho khách nên bị hoàn về"); khớp với nhóm (b). Địa chỉ cũ chỉ có nguồn phỏng vấn.
