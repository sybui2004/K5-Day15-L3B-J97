# Data card — dữ liệu bản chạy thử dùng

> Điền ở guide bước 2.4 (bản đầu ở CP2, đủ ở CP3). Ôn lại: ngày 6 · lab ngày 6. Chấm ở rubric R4.
> Một trang. Mỗi dataset một mục. Dữ liệu chạy thử (bài mẫu, thông báo mẫu, đoạn transcript…) để trong thư mục `data/` này.
> Không commit nguyên tài liệu khoá, dữ liệu cá nhân thật hay nguyên file data BTC cấp — chỉ đoạn trích ngắn, bản viết lại, hoặc số đã tổng hợp.

## Dataset 1 · Hội thoại chốt đơn (`eval/benchmark.csv`)

| | |
|---|---|
| Dùng để làm gì | bộ câu thử: quyết định TẠO ĐƠN NHÁP, HỎI LẠI hoặc TỪ CHỐI trước khi tạo đơn nháp và vận đơn nháp |
| Từ đâu | Chưa dùng đoạn chat trong `evidence/interviews/P1.md`–`P4.md` (phỏng vấn 4 chủ shop ngày 27/11/2026, có 8 đoạn chat đã che); sẽ đưa vào khi mở rộng bộ câu thử cho CP3. **12 câu nhóm tự viết** (`tu_viet`, B03, B05–B15). **7 câu ghép từ văn bản công khai** (`data_that`): B01, B02, B04 lấy ví dụ địa chỉ trên https://since98.vn/vi/cong-cu/chuyen-doi-dia-chi-sau-sap-nhap ("12 Nguyễn Huệ, P. Bến Nghé, Q.1, TP.HCM" → "12 Nguyễn Huệ, Phường Sài Gòn, Thành phố Hồ Chí Minh"; trang nói ví dụ dùng được khi không dấu). B16–B19 lấy nguyên văn review App Store của GHN qua https://opportunitymarket.org/vi/ung-dung/ghn (người dùng 5ef8 ngày 22/05/2026, cc8d, 585f app v4.14.0, 2638 app v4.13.9) |
| Xử lý những bước gì | Bộ câu thử hiện chưa dùng tin thật của shop nên chưa cần che. Tên (Lan, Hoa, Mai, Hùng), số điện thoại, số nhà và mã `KH-xxx` là giá trị dựng, không có trên trang nguồn. Câu since98 chỉ giữ cụm địa chỉ công khai, rồi bọc thành một dòng input. Câu review GHN giữ câu khiếu nại, không chép biệt danh đầy đủ, bọc thành một dòng input. Phường cũ và phường mới trong câu tự viết lấy từ `data/chuyen-doi-dia-gioi.csv`, trừ B13 cố ý dùng Phường 99 (không có trong bảng) |
| Số dòng / số đoạn | 19 câu: thuong 4 · kho 9 · tu_choi 6. Nguồn: `tu_viet` 12 · `data_that` 7 · `nguoi_dung` 0 · `sinh_seed` 0 |
| Phiên bản / ngày lấy | since98 và opportunitymarket lấy ngày 27/11/2026. 12 câu tự viết viết cùng ngày, theo lưới input ở `docs/cp2-ke-hoach.md` mục Y3 |
| Nhãn | `synthetic` cho hội thoại, tên, số điện thoại, số nhà. Cụm địa chỉ since98 và câu review GHN là trích công khai, không phải tin khách chốt đơn của shop |
| Giới hạn | Không đo pain của chủ shop và không thay phỏng vấn. Review GHN là khiếu nại app giao hàng hoặc xin số người khác, không phải tin chốt mua. since98 là ví dụ công cụ chuyển địa chỉ, không phải đơn hàng. 12 câu tự viết có thể lệch cách khách nhắn thật |

**Data `synthetic`:** viết tay theo lưới Y3 (kiểu địa chỉ, mức thiếu, độ lộn xộn, người nhận, hành vi mong đợi). Không có script sinh và không có seed. Đã đối tên phường trong câu địa chỉ với `data/chuyen-doi-dia-gioi.csv`. Data tự dựng **không phải bằng chứng pain**.

## Dataset 2 · Bảng chuyển đổi địa giới TP Hồ Chí Minh (`data/chuyen-doi-dia-gioi.csv`)

| | |
|---|---|
| Dùng để làm gì | nguồn cho công cụ `convert_old_address` và `lookup_address` · tên phường cũ/mới cho bộ câu thử |
| Từ đâu | **Nguồn chính:** Nghị quyết 1685/NQ-UBTVQH15 ngày 16/6/2025 về sắp xếp ĐVHC cấp xã của TP Hồ Chí Minh, Điều 1 (khoản 1–164), toàn văn trên Cổng TTĐT Chính phủ: https://xaydungchinhsach.chinhphu.vn/toan-van-nghi-quyet-so-1685-nq-ubtvqh15-sap-xep-cac-dvhc-cap-xa-cua-thanh-pho-ho-chi-minh-nam-2025-119250616211341304.htm (chép lại ở `data/nguon/nq1685-dieu1.txt`). **Nguồn phụ** (chỉ để biết quận/huyện cũ và tỉnh cũ): Bảng chuyển đổi ĐVHC mới–cũ của Cục Thống kê, https://danhmuchanhchinh.nso.gov.vn/ → file `BangChuyendoiĐVHCmoi_cu_final.xlsx`, sheet "Tổng hợp_không merge" (phần TP HCM trích ở `data/nguon/cuc-thong-ke-hcm.csv`) |
| Xử lý những bước gì | bỏ HTML, chuẩn hoá Unicode NFC · script `data/nguon/tach_nq1685.py` tách từng khoản thành dòng cũ → mới, lấy kiểu sắp xếp theo chữ của văn bản ("toàn bộ" / "một phần" / "phần còn lại") · quận/huyện cũ: lấy từ văn bản nếu ghi ngay sau tên phường (`nguon_quan=van_ban`, 154 dòng), còn lại tra bảng Cục Thống kê theo cặp (phường mới, phường cũ) (`nguon_quan=cuc_thong_ke`, 339 dòng) · tỉnh cũ: theo bảng Cục Thống kê · trích bảng Cục Thống kê: `data/nguon/trich_cuc_thong_ke.py` |
| Số dòng / số đoạn | 493 dòng · 164 khoản · 163 đơn vị mới hình thành (112 phường, 50 xã, 1 đặc khu, khớp số ở khoản 164) + 5 đơn vị không sắp xếp (khoản 164, `kieu=khong_sap_xep`) · theo tỉnh cũ: TP HCM 308, Bình Dương 107, Bà Rịa - Vũng Tàu 78 · kiểu: `toan_bo` 390, `mot_phan` 51, `phan_con_lai` 47 · **47 phường/xã cũ bị tách** (có ≥2 dòng) |
| Kiểm tra | (1) đối chiếu chéo toàn bộ với bảng Cục Thống kê: cùng 493 cặp (phường mới, phường cũ), không thừa không thiếu; 154 dòng văn bản có ghi quận (kể cả dòng huyện Côn Đảo) đều trùng quận của Cục Thống kê · script tự kiểm (1), (2), đủ khoản 1–164 và không có dòng trùng ở bảng Cục Thống kê; lệch bất kỳ chỗ nào thì dừng với mã 1 và không ghi file · (2) mỗi phường bị tách có ≥1 dòng `mot_phan` và đúng 1 dòng `phan_con_lai` · (3) đối chiếu tay với văn bản **29 khoản**: 1, 2, 3, 4, 5, 9, 16, 22, 24, 38, 39, 41, 43, 45, 63, 71, 80, 82, 93, 101, 102, 106, 116, 122, 134, 144, 152, 163, 164 (có cả khoản `mot_phan`/`phan_con_lai`, khoản không ghi quận như 1, 71, 80, khoản trộn quận như 16, 24, 116). Người kiểm: Hưng |
| Phiên bản / ngày lấy | Nghị quyết 1685/NQ-UBTVQH15 (16/6/2025) · lấy cả hai nguồn ngày 27/11/2026 |
| Nhãn | thật (văn bản pháp luật công khai, không có dữ liệu cá nhân) |
| Giới hạn | chỉ TP Hồ Chí Minh sau sắp xếp (gồm địa bàn Bình Dương, Bà Rịa - Vũng Tàu cũ), không đủ cả nước · văn bản **không nói đường/khu phố nào thuộc phần nào** của phường bị tách, nên bảng chỉ cho danh sách phường mới có thể, không chọn được một · tên quận/huyện là tên ngay trước 1/7/2025 (vd `huyện Long Đất`, `thành phố Thủ Đức`); khách ghi tên cũ hơn (vd "quận 2", "quận 9", "huyện Đất Đỏ") thì bảng không có · dòng khoản 163 (huyện Côn Đảo → đặc khu Côn Đảo) để trống `phuong_xa_cu` vì đơn vị cũ là cả huyện · một số tên phường cũ trùng nhau giữa các quận (vd `Phường 1`, `phường Tân Phú`, `phường An Phú`), tra phải có quận |

## Dataset 3 · Hộp thư mẫu cho luồng A (`data/hop-thu-mau.jsonl`)

| | |
|---|---|
| Dùng để làm gì | đầu vào chạy thử `xu_ly_hop_thu` (`codebase/inbox.py`) và màn hình duyệt (D). Không phải bộ câu thử để chấm: không tính vào số câu của Dataset 1 |
| Từ đâu | **sinh bằng trợ lý AI:** Claude Code (model Claude Sonnet 5.5), ngày 27/11/2026, theo yêu cầu "làm P1 hộp thư" và mô tả task P1 trong `docs/cp2-ke-hoach.md`; không lấy từ chat thật |
| Xử lý những bước gì | trợ lý AI soạn từng hội thoại và ghi ra file bằng một script một lần (không lưu trong repo); không dùng seed, không người nào viết tay · mỗi dòng `{ma_hoi_thoai, ma_khach, luot: [{vai, tin}]}` · text một dòng do `doc_hop_thu` ghép, mã khách chỉ lấy từ `ma_khach` |
| Số dòng / số đoạn | 10 hội thoại (HT-01 … HT-10). Ý định: nên ra đơn nháp HT-01, 02, 03, 06 · nên hỏi lại HT-04 (thiếu sđt), 05 (phường bị tách chưa chọn), 07 (đổi người nhận, sđt 9 số), 10 (thiếu địa chỉ; tin có dấu gạch đứng và mã khách người khác) · nên từ chối HT-08 (đòi bỏ qua kiểm tra), 09 (xin thông tin khách khác) |
| Kiểm tra | đối chiếu **bằng công cụ** X2 / bảng X0: 10/10 dòng khớp ý định (review PR #18, `hgmdz1210`) · **người kiểm tay: chưa có** · số dòng kiểm tay: 0 |
| Chạy thử bằng model thật | 27/11, `claude-sonnet-5-5`, effort `low`, chạy 1 lần: 9/10 ra đúng ý định. HT-10 ra từ chối thay vì hỏi lại: model coi tin nhắn có mã khách người khác là yêu cầu ngoài phạm vi (không tạo đơn nháp) · câu trả lời model và kết quả từng câu: `data/hop-thu-mau-chay-thu.json` |
| Phiên bản / ngày lấy | 27/11/2026 |
| Nhãn | `synthetic` |
| Giới hạn | tên, số điện thoại, số nhà, số hẻm, số đường là giá trị dựng (số điện thoại bắt đầu bằng `090000`; HT-07 cố ý có một số chỉ 9 chữ số); tên phường lấy từ Dataset 2 · không trùng Dataset 1 về mã khách, số điện thoại và tin khách nhắn · câu chữ gọn hơn chat thật · **không phải bằng chứng pain** |

**Data `synthetic`:** sinh bằng trợ lý AI (công cụ, model, ngày, yêu cầu ghi ở dòng "Từ đâu"), không có seed; script ghi file chạy một lần và không lưu trong repo nên không sinh lại y hệt được. Đã đối chiếu bằng công cụ 10/10 hội thoại; người kiểm tay: chưa có (0 dòng). Data tự dựng **không phải bằng chứng pain**.
