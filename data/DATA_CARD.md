# Data card — dữ liệu bản chạy thử dùng

> Điền ở guide bước 2.4 (bản đầu ở CP2, đủ ở CP3). Ôn lại: ngày 6 · lab ngày 6. Chấm ở rubric R4.
> Một trang. Mỗi dataset một mục. Dữ liệu chạy thử (bài mẫu, thông báo mẫu, đoạn transcript…) để trong thư mục `data/` này.
> Không commit nguyên tài liệu khoá, dữ liệu cá nhân thật hay nguyên file data BTC cấp — chỉ đoạn trích ngắn, bản viết lại, hoặc số đã tổng hợp.

## Dataset 1 · [tên]

| | |
|---|---|
| Dùng để làm gì | nguồn cho công cụ `…` · bộ câu thử · đào bằng chứng |
| Từ đâu | data BTC cấp (`…` trong repo đề) · tài liệu khoá (trích / viết lại) · nhóm tự viết · sinh có seed |
| Xử lý những bước gì | lọc __ · làm sạch __ · ẩn danh __ · chia __ (script: `…`) |
| Số dòng / số đoạn | __ |
| Phiên bản / ngày lấy | __ |
| Nhãn | thật · `synthetic` |
| Giới hạn | thiếu gì, lệch về phía nào |

**Data `synthetic` (nhóm tự sinh):** ghi cách sinh (prompt / script), seed, người kiểm, số dòng đã kiểm tay. Data tự dựng **không phải bằng chứng pain**.

## Dataset 2 · Bảng chuyển đổi địa giới TP Hồ Chí Minh (`data/chuyen-doi-dia-gioi.csv`)

| | |
|---|---|
| Dùng để làm gì | nguồn cho công cụ `convert_old_address` và `lookup_address` · tên phường cũ/mới cho bộ câu thử |
| Từ đâu | **Nguồn chính:** Nghị quyết 1685/NQ-UBTVQH15 ngày 16/6/2025 về sắp xếp ĐVHC cấp xã của TP Hồ Chí Minh, Điều 1 (khoản 1–164), toàn văn trên Cổng TTĐT Chính phủ: https://xaydungchinhsach.chinhphu.vn/toan-van-nghi-quyet-so-1685-nq-ubtvqh15-sap-xep-cac-dvhc-cap-xa-cua-thanh-pho-ho-chi-minh-nam-2025-119250616211341304.htm (chép lại ở `data/nguon/nq1685-dieu1.txt`). **Nguồn phụ** (chỉ để biết quận/huyện cũ và tỉnh cũ): Bảng chuyển đổi ĐVHC mới–cũ của Cục Thống kê, https://danhmuchanhchinh.nso.gov.vn/ → file `BangChuyendoiĐVHCmoi_cu_final.xlsx`, sheet "Tổng hợp_không merge" (phần TP HCM trích ở `data/nguon/cuc-thong-ke-hcm.csv`) |
| Xử lý những bước gì | bỏ HTML, chuẩn hoá Unicode NFC · script `data/nguon/tach_nq1685.py` tách từng khoản thành dòng cũ → mới, lấy kiểu sắp xếp theo chữ của văn bản ("toàn bộ" / "một phần" / "phần còn lại") · quận/huyện cũ: lấy từ văn bản nếu ghi ngay sau tên phường (`nguon_quan=van_ban`, 154 dòng), còn lại tra bảng Cục Thống kê theo cặp (phường mới, phường cũ) (`nguon_quan=cuc_thong_ke`, 339 dòng) · tỉnh cũ: theo bảng Cục Thống kê · trích bảng Cục Thống kê: `data/nguon/trich_cuc_thong_ke.py` |
| Số dòng / số đoạn | 493 dòng · 164 khoản · 163 đơn vị mới hình thành (112 phường, 50 xã, 1 đặc khu, khớp số ở khoản 164) + 5 đơn vị không sắp xếp (khoản 164, `kieu=khong_sap_xep`) · theo tỉnh cũ: TP HCM 308, Bình Dương 107, Bà Rịa - Vũng Tàu 78 · kiểu: `toan_bo` 390, `mot_phan` 51, `phan_con_lai` 47 · **47 phường/xã cũ bị tách** (có ≥2 dòng) |
| Kiểm tra | (1) đối chiếu chéo toàn bộ với bảng Cục Thống kê: cùng 493 cặp (phường mới, phường cũ), không thừa không thiếu; 154 dòng văn bản có ghi quận đều trùng quận của Cục Thống kê · (2) mỗi phường bị tách có ≥1 dòng `mot_phan` và đúng 1 dòng `phan_con_lai` · (3) đối chiếu tay với văn bản **29 khoản**: 1, 2, 3, 4, 5, 9, 16, 22, 24, 38, 39, 41, 43, 45, 63, 71, 80, 82, 93, 101, 102, 106, 116, 122, 134, 144, 152, 163, 164 (có cả khoản `mot_phan`/`phan_con_lai`, khoản không ghi quận như 1, 71, 80, khoản trộn quận như 16, 24, 116). Người kiểm: Hưng |
| Phiên bản / ngày lấy | Nghị quyết 1685/NQ-UBTVQH15 (16/6/2025) · lấy cả hai nguồn ngày 27/11/2026 |
| Nhãn | thật (văn bản pháp luật công khai, không có dữ liệu cá nhân) |
| Giới hạn | chỉ TP Hồ Chí Minh sau sắp xếp (gồm địa bàn Bình Dương, Bà Rịa - Vũng Tàu cũ), không đủ cả nước · văn bản **không nói đường/khu phố nào thuộc phần nào** của phường bị tách, nên bảng chỉ cho danh sách phường mới có thể, không chọn được một · tên quận/huyện là tên ngay trước 1/7/2025 (vd `huyện Long Đất`, `thành phố Thủ Đức`); khách ghi tên cũ hơn (vd "quận 2", "quận 9", "huyện Đất Đỏ") thì bảng không có · dòng khoản 163 (huyện Côn Đảo → đặc khu Côn Đảo) để trống `phuong_xa_cu` vì đơn vị cũ là cả huyện · một số tên phường cũ trùng nhau giữa các quận (vd `Phường 1`, `phường Tân Phú`, `phường An Phú`), tra phải có quận |
