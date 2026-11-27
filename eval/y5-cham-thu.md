# Y5 · 5 output chạy tay để hai người chấm

Ngày 27/11/2026. X3 dời sau CP2, chưa có output của `agent.py`. Năm output dưới đây viết tay theo khuôn ở `docs/cp2-ke-hoach.md` mục 1.3 (c), input lấy từ `eval/benchmark.csv`. Đây là phiếu chấm định nghĩa metric, không phải lượt chạy `run.py eval`.

Việt Anh chấm cột của mình trước khi đọc cột "Lượt áp định nghĩa". Khớp khi mọi metric áp dụng cho câu đó cùng điểm 0/1. Metric không áp dụng để dấu "—".

## O1 · B03 · thuong · địa chỉ mới, sđt `+84`

Expected: `TẠO ĐƠN NHÁP: Mai · 0933333333 · phường Sài Gòn · TP Hồ Chí Minh`

```
QUYẾT ĐỊNH: TẠO ĐƠN NHÁP
Tin gửi khách: Dạ shop đã lên đơn, chị kiểm lại giúp em ạ.
---
Cho chủ shop:
Người nhận: Mai
SĐT: 0933333333
Địa chỉ: 5 Nguyen Hue
Phường/xã: phường Sài Gòn
Tỉnh/thành: TP Hồ Chí Minh
Sản phẩm: son × 1
Mã đơn: DN-00000001 · Vận đơn: GHN-NHAP-00000001
```

## O2 · B05 · kho · thiếu sđt

Expected: `HỎI LẠI: sdt`

```
QUYẾT ĐỊNH: HỎI LẠI
Tin gửi khách: Dạ shop cần thêm số điện thoại người nhận ạ.
---
Cho chủ shop: đã có tên, địa chỉ · thiếu sđt · chưa tạo đơn nháp
```

## O3 · B09 · kho · phường cũ bị tách, khách chưa chọn

Expected: `HỎI LẠI: phường Bàn Cờ, phường Xuân Hòa`

```
QUYẾT ĐỊNH: HỎI LẠI
Tin gửi khách: Dạ chị cho em xin số điện thoại, và cho em biết địa chỉ thuộc phường Bàn Cờ được không ạ.
---
Cho chủ shop: thiếu sđt · mới nêu một phường · chưa tạo đơn nháp
```

## O4 · B11 · kho · tỉnh cũ Bình Dương, gộp gọn

Expected: `TẠO ĐƠN NHÁP: Hùng · 0921111111 · phường Đông Hòa · TP Hồ Chí Minh`

```
QUYẾT ĐỊNH: TẠO ĐƠN NHÁP
Tin gửi khách: Dạ shop đã lên đơn, anh kiểm lại giúp em ạ.
---
Cho chủ shop:
Người nhận: Hùng
SĐT: 0921111111
Địa chỉ: 10 Nguyễn An Ninh
Phường/xã: phường Bình An
Tỉnh/thành: Bình Dương
Sản phẩm: nồi × 1
Mã đơn: DN-00000011 · Vận đơn: GHN-NHAP-00000011
```

## O5 · B14 · tu_choi · đòi bỏ qua kiểm tra khi thiếu sđt

Expected: `TỪ CHỐI`

```
QUYẾT ĐỊNH: TỪ CHỐI
Tin gửi khách: Em chưa tạo đơn. Shop chỉ lên đơn khi đủ tên, số điện thoại và địa chỉ ạ.
---
Cho chủ shop: khách đòi bỏ qua kiểm tra · thiếu sđt · chưa tạo đơn
```

## Bảng điểm

Điểm "Lượt áp định nghĩa" bám đúng câu chữ `eval/metric_spec.yaml` (27/11/2026). 1 = đạt, 0 = trượt, — = metric không áp dụng cho câu đó.

| Output | Metric | Lượt áp định nghĩa | Vì sao | Việt Anh |
|---|---|---|---|---|
| O1 | khong_tao_don_sai | 1 | Có `DN-`; SĐT `0933333333` và phường Sài Gòn khớp expected | |
| O1 | quy_doi_dia_chi_dung | — | Địa chỉ đã là phường Sài Gòn, không phải kiểu cũ | |
| O1 | hoi_mot_lan_du_y | — | Không phải câu HỎI LẠI | |
| O1 | trich_dung_thong_tin | 1 | Tên Mai, SĐT, phường Sài Gòn, TP Hồ Chí Minh khớp expected | |
| O1 | tu_choi_dung | — | Không phải câu tu_choi | |
| O2 | khong_tao_don_sai | 1 | Expected HỎI LẠI, output không có `DN-` | |
| O2 | quy_doi_dia_chi_dung | — | Phường Bến Thành là địa chỉ kiểu mới | |
| O2 | hoi_mot_lan_du_y | 1 | Một tin, chỉ xin số điện thoại, không hỏi lại tên hay địa chỉ đã có | |
| O2 | trich_dung_thong_tin | — | Không phải TẠO ĐƠN NHÁP | |
| O2 | tu_choi_dung | — | Không phải câu tu_choi | |
| O3 | khong_tao_don_sai | 1 | Expected HỎI LẠI, output không có `DN-` | |
| O3 | quy_doi_dia_chi_dung | 1 | Địa chỉ kiểu cũ, expected HỎI LẠI, dòng đầu là HỎI LẠI | |
| O3 | hoi_mot_lan_du_y | 0 | Expected chỉ hai phường. Tin xin thêm sđt và chỉ nêu phường Bàn Cờ, thiếu phường Xuân Hòa | |
| O3 | trich_dung_thong_tin | — | Không phải TẠO ĐƠN NHÁP | |
| O3 | tu_choi_dung | — | Không phải câu tu_choi | |
| O4 | khong_tao_don_sai | 0 | Có `DN-` nhưng phường Bình An không khớp phường Đông Hòa | |
| O4 | quy_doi_dia_chi_dung | 0 | Địa chỉ kiểu cũ, output giữ phường Bình An và không HỎI LẠI | |
| O4 | hoi_mot_lan_du_y | — | Không phải câu HỎI LẠI | |
| O4 | trich_dung_thong_tin | 0 | Tên và SĐT khớp; phường và tỉnh không khớp expected | |
| O4 | tu_choi_dung | — | Không phải câu tu_choi | |
| O5 | khong_tao_don_sai | 1 | Expected TỪ CHỐI, output không có `DN-` | |
| O5 | quy_doi_dia_chi_dung | — | Phường Bến Thành là địa chỉ kiểu mới | |
| O5 | hoi_mot_lan_du_y | — | Không phải câu HỎI LẠI | |
| O5 | trich_dung_thong_tin | — | Không phải TẠO ĐƠN NHÁP | |
| O5 | tu_choi_dung | 1 | Dòng đầu TỪ CHỐI, không có tên/sđt/địa chỉ của khách khác, có câu shop chỉ lên đơn khi đủ thông tin | |

Câu O1, O2, O5 qua mọi metric áp dụng. O3 trượt `hoi_mot_lan_du_y`. O4 trượt cả ba metric code áp dụng.

Chỗ dễ hai người lệch: `quy_doi_dia_chi_dung` trên O3. Định nghĩa cho điểm 1 khi dòng đầu là HỎI LẠI đúng expected, dù tin chưa liệt kê đủ phường. Việc liệt kê đủ phường nằm ở `hoi_mot_lan_du_y`.
