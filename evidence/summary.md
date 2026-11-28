# Tổng hợp bằng chứng pain

> Điền ở guide bước 1.2, xong trước **CP3 10:00 Thứ Bảy 28/11**. Chấm ở rubric R1.
> Ba nguồn ngang nhau — tối thiểu **≥1 nguồn đạt ngưỡng**. Mạnh nhất: đào data ra insight → hỏi người dùng để kiểm lại (hoặc ngược lại).

## 1. Nguồn đã dùng

| Nguồn | Đạt ngưỡng? | File |
|---|---|---|
| Đào data (x/N, %, cách đếm chạy lại được, ≥5 ví dụ) | ☑ nguồn kiểm chéo: 100 review mới nhất app GHN trên Google Play, đếm 28/11 · **7/100 (7%)** kể sai / thiếu thông tin nhận hàng | `evidence/data-mining.md` · `evidence/review-ghn.csv` · `evidence/count_review.py` |
| Phỏng vấn (≥3 người ngoài nhóm, đúng người dùng) | ☑ nguồn chính · **4 chủ shop bán lẻ ở TP HCM, phỏng vấn 27/11** | `evidence/interviews/P1.md`–`P4.md` · câu hỏi: `docs/question.md` |
| Khảo sát (≥20 người ngoài nhóm, đúng người dùng) | — không làm | — |

## 2. Số chính

- Đào data: **7/100 (7%)** review GHN mới nhất (16/10–26/11/2026) kể chuyện sai hoặc thiếu thông tin nhận hàng: 2 nhầm mã vận đơn, 5 nêu lý do giao thất bại là "không liên lạc được người nhận". **0/100** nhắc địa chỉ sau sáp nhập. Đối chiếu nhãn 20 review đầu: lệch 3/20, dưới ngưỡng 4/20; Sỹ duyệt toàn bộ nhãn.
- Phỏng vấn (n = 4, không ghi %):
  - **H2 (chép sai, thiếu thông tin nhận hàng): 4/4 người gặp trong 1 tháng qua.** Số lần / tháng: P1 3, P2 4, P3 2, P4 1. Mỗi vụ mất 38.000–60.000đ phí ship, 3/4 vụ gần nhất khách huỷ hoặc mua chỗ khác.
  - **H1 (trả lời chậm khi đông khách → khách bỏ): 1/4 kể rõ** (P4: 2 lần / tháng khách bỏ vì trả lời chậm 15–20 phút). 3/4 còn lại kể **một phần**: lúc đông khách thì lên đơn vội gây sai, và khách bỏ khi bị hỏi lại nhiều lần (P2: khoảng 30% khách không trả lời sau lần hỏi lại thứ hai).
  - **Người nhận khác người đặt bị chép nhầm: 4/4 kể được một vụ** (P3: vụ ở tháng trước, ngoài 1 tháng qua).
  - **Địa chỉ kiểu cũ: 4/4 nói khách vẫn ghi**, ước 20%, 30%, 35–40%, 45% đơn; mỗi đơn như vậy thêm 1–3 phút. **4/4 kể từng quy đổi sai hoặc GHN không nhận phường cũ** (P1 2 lần / tháng chọn nhầm phường giáp ranh).
  - Mỗi đơn qua tin nhắn: 4–8 phút, 3–6 lượt nhắn. Đơn / tháng: 260–650 (P1 480, P2 650, P3 320, P4 260).
- Khảo sát: không làm.

Phỏng vấn nhiều vai thì đếm theo từng vai, không cộng chung.

| | Vai | Gặp pain? | Số lần / 1 tháng qua | Lần gần nhất mất | Đang xoay xở bằng |
|---|---|---|---|---|---|
| P1 | chủ shop thời trang nữ | H2 có · H1 một phần | 3 | 5–6 phút / đơn; vụ hoàn: 52.000đ + khách huỷ | copy-paste sang GHN, tự tra Google phường mới |
| P2 | chủ shop phụ kiện điện thoại | H2 có · H1 một phần | 4 | khoảng 4 phút / đơn; vụ hoàn: 45.000đ + khách huỷ | copy-paste / gõ tay, tab tra cứu đơn vị hành chính |
| P3 | chủ shop mỹ phẩm | H2 có · H1 một phần | 2 | 7–8 phút / đơn; vụ hoàn: 60.000đ + hàng móp | chép ra sổ rồi gõ vào GHN, hỏi lại khách phường mới |
| P4 | chủ shop đồ gia dụng | H2 có · H1 có | 1 hoàn + 2 bỏ vì trả lời chậm | 4–5 phút / đơn; vụ hoàn: 38.000đ | copy-paste sang GHN, bảng quy đổi lưu trên máy |

## 3. ≥5 trích dẫn hoặc ví dụ nguyên văn (có nguồn, bỏ tên)

1. "mình vừa trả lời tư vấn vừa lên đơn gấp nên copy nhầm số điện thoại của chị đặt váy sang đơn của bạn đặt áo" — P1
2. "Khách bị hỏi lại 2–3 lần là hay im lặng bỏ ngang lắm, nhất là buổi tối." — P1
3. "Tầm 30% khách bị hỏi lại lần thứ hai là im luôn không rep nữa." — P2
4. "Có mấy lần hệ thống GHN không nhận tên phường cũ khách gửi, bắt buộc phải dò đúng tên phường mới sau sáp nhập mới cho tạo mã vận đơn." — P2
5. "mình nhìn nhầm số 8 thành số 3 ở đuôi; đơn gửi đi ngoại tỉnh nằm ở bưu cục 4 ngày không gọi được cho khách nên bị hoàn về." — P3
6. "có thêm 2 lần khách bỏ không mua nữa vì lúc cao điểm mình trả lời chậm 15–20 phút." — P4
7. "do khách nhắn gộp 2–3 câu trong một đoạn nên lúc copy nhanh mình lấy nhầm dòng trên." — P4

Cả 4 người đồng ý cho trích nguyên văn, không ghi tên người và tên shop (câu 15).

## 4. Các nguồn có khớp nhau không

**Khớp một phần.** Review GHN (7/100) cho thấy thông tin nhận hàng sai hoặc không liên lạc được người nhận làm đơn bị hoàn, khớp với phỏng vấn: 4/4 shop có vụ chép sai, P3 có đơn hoàn vì "không gọi được cho khách". **Lệch:** review do người nhận / người gửi lẻ viết, phàn nàn về khâu giao của GHN, nên không tách được phần do shop chép sai; nhóm "không liên lạc được" có thể do shipper không gọi. Địa chỉ kiểu cũ: phỏng vấn 4/4, review 0/100, vì người viết review không kể khâu shop nhập địa chỉ, nên con số 20–45% chỉ có nguồn phỏng vấn. Trong 4 buổi phỏng vấn, các con số tự khớp nhau ở H2 (4/4) và ở địa chỉ kiểu cũ (4/4); lệch ở H1 (chỉ P4 kể rõ khách bỏ vì trả lời chậm).

## 5. Kết luận

Giả thuyết ở `evidence/hypothesis.md`:
- **H2 đúng** — 4/4 chủ shop kể được ít nhất 1 lần chép sai hoặc thiếu thông tin nhận hàng trong 1 tháng qua (ngưỡng ≥2/3). Đây là pain lát cắt nhắm vào.
- **H1 phải đổi** — chỉ 1/4 kể rõ khách bỏ vì trả lời chậm (dưới ngưỡng ≥2/3). Cái 3/4 kể là **khách bỏ khi bị hỏi lại nhiều lần**. Vì vậy tin hỏi lại phải gom đủ trường trong **một** tin (metric `hoi_mot_lan_du_y`).
- **Thêm điều chưa có trong giả thuyết:** địa chỉ kiểu cũ (20–45% đơn) làm mỗi đơn chậm thêm 1–3 phút và gây quy đổi sai — đúng chỗ khó lát cắt chọn.

Điều vẫn chưa biết: phần lỗi do shop chép sai trong các vụ hoàn (review không tách được); tỉ lệ đơn địa chỉ cũ ngoài 4 shop; n = 4 là nhỏ và cả 4 đều ở TP HCM.

## Lịch hẹn (dùng cho CP2 — chỉ ghi vai và giờ, không tên)

| Vai | Giờ hẹn | Đã xong? |
|---|---|---|
| P1 · chủ shop thời trang nữ | 27/11, 12:00 (gọi điện) | ☑ |
| P2 · chủ shop phụ kiện điện thoại | 27/11, 12:30 (trực tiếp) | ☑ |
| P3 · chủ shop mỹ phẩm | 27/11, 14:00 (video) | ☑ |
| P4 · chủ shop đồ gia dụng | 27/11, 14:00 (trực tiếp) | ☑ |

**Tình trạng lúc CP2:** đã viết giả thuyết trước khi hỏi (`evidence/hypothesis.md`, commit `555b0aa`) · đã phỏng vấn 4 chủ shop bán lẻ ở TP HCM theo bộ 15 câu hỏi ở `docs/question.md` · đã viết cách đếm review Google Play trước khi đếm, chưa đếm.
