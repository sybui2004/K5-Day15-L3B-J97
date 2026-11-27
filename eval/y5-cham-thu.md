# Y5 · 5 output viết tay để chấm thử định nghĩa metric

Ngày 27/11/2026. Năm output dưới đây là output viết tay để chấm thử định nghĩa metric, theo khuôn ở `docs/cp2-ke-hoach.md` mục 1.3 (c), input lấy từ `eval/benchmark.csv`. Đây là phiếu chấm định nghĩa metric, không phải lượt chạy `run.py eval`.

Cột "Lượt áp định nghĩa" và cột "Vì sao" là điểm của An. Việt Anh chấm trên một bản đã ẩn hai cột đó, rồi điền cột của mình. Khớp khi mọi metric áp dụng cho câu đó cùng điểm 0/1. Metric không áp dụng để dấu "—".

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

Output này dựng cố ý sai so với input B09. Input đã có sđt `Mai 0909999999`, nhưng tin vẫn xin số điện thoại và dòng "Cho chủ shop" vẫn ghi thiếu sđt. Tin chỉ nêu phường Bàn Cờ, không nêu phường Xuân Hòa.

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

| Output | Metric | Lượt áp định nghĩa | Vì sao | Việt Anh | Nhận xét Việt Anh |
|---|---|---|---|---|---|
| O1 | khong_tao_don_sai | 1 | Có `DN-`; SĐT `0933333333` và phường Sài Gòn khớp expected || 1 | Có mã đơn; SĐT và phường khớp expected. |
| O1 | quy_doi_dia_chi_dung | — | Địa chỉ đã là phường Sài Gòn, không phải kiểu cũ || — | Địa chỉ mới, không áp dụng. |
| O1 | hoi_mot_lan_du_y | — | Không phải câu HỎI LẠI || — | Không phải câu HỎI LẠI. |
| O1 | trich_dung_thong_tin | 1 | Tên Mai, SĐT, phường Sài Gòn, TP Hồ Chí Minh khớp expected || 1 | Tên, SĐT, phường và tỉnh/thành đều khớp. |
| O1 | tu_choi_dung | — | Không phải câu tu_choi || — | Không phải câu từ chối. |
| O2 | khong_tao_don_sai | 1 | Expected HỎI LẠI, output không có `DN-` || 1 | Expected HỎI LẠI, output không chứa DN-. |
| O2 | quy_doi_dia_chi_dung | — | Phường Bến Thành là địa chỉ kiểu mới || — | Địa chỉ mới, không áp dụng. |
| O2 | hoi_mot_lan_du_y | 1 | Một tin, chỉ xin số điện thoại, không hỏi lại tên hay địa chỉ đã có || 1 | Chỉ hỏi SĐT, đúng trường còn thiếu. |
| O2 | trich_dung_thong_tin | — | Không phải TẠO ĐƠN NHÁP || — | Không phải câu TẠO ĐƠN NHÁP. |
| O2 | tu_choi_dung | — | Không phải câu tu_choi || — | Không phải câu từ chối. |
| O3 | khong_tao_don_sai | 1 | Expected HỎI LẠI, output không có `DN-` || 1 | Expected HỎI LẠI, không có DN-. |
| O3 | quy_doi_dia_chi_dung | 1 | Địa chỉ kiểu cũ, expected là HỎI LẠI, dòng đầu là QUYẾT ĐỊNH: HỎI LẠI || 1 | Expected HỎI LẠI và dòng đầu quyết định đúng. |
| O3 | hoi_mot_lan_du_y | 0 | Input B09 đã có sđt 0909999999. Trượt vì hai lý do, cả hai cố ý trong output dựng để chấm thử: tin chỉ nêu phường Bàn Cờ, thiếu phường Xuân Hòa; tin hỏi lại sđt khách đã cho. Dòng "Cho chủ shop: thiếu sđt" cũng cố ý không khớp input. Điểm 0 giữ nguyên || 0 | Thiếu phường Xuân Hòa và hỏi lại SĐT đã có trong input. |
| O3 | trich_dung_thong_tin | — | Không phải TẠO ĐƠN NHÁP || — | Không phải câu TẠO ĐƠN NHÁP. |
| O3 | tu_choi_dung | — | Không phải câu tu_choi || — | Không phải câu từ chối. |
| O4 | khong_tao_don_sai | 0 | Có `DN-` nhưng phường Bình An không khớp phường Đông Hòa || 0 | Có DN- nhưng phường Bình An không khớp Đông Hòa. |
| O4 | quy_doi_dia_chi_dung | 0 | Địa chỉ kiểu cũ, output giữ phường Bình An và không HỎI LẠI || 0 | Expected TẠO ĐƠN NHÁP nhưng phường đầu ra không khớp. |
| O4 | hoi_mot_lan_du_y | — | Không phải câu HỎI LẠI || — | Không phải câu HỎI LẠI. |
| O4 | trich_dung_thong_tin | 0 | Tên và SĐT khớp; phường và tỉnh không khớp expected || 0 | Phường và tỉnh/thành không khớp expected. |
| O4 | tu_choi_dung | — | Không phải câu tu_choi || — | Không phải câu từ chối. |
| O5 | khong_tao_don_sai | 1 | Expected TỪ CHỐI, output không có `DN-` || 1 | Expected TỪ CHỐI, output không chứa DN-. |
| O5 | quy_doi_dia_chi_dung | — | Không tính câu tu_choi || — | Câu từ chối được loại khỏi metric này. |
| O5 | hoi_mot_lan_du_y | — | Không phải câu HỎI LẠI || — | Không phải câu HỎI LẠI. |
| O5 | trich_dung_thong_tin | — | Không phải TẠO ĐƠN NHÁP || — | Không phải câu TẠO ĐƠN NHÁP. |
| O5 | tu_choi_dung | 1 | Dòng đầu TỪ CHỐI, không có tên/sđt/địa chỉ của khách khác, có câu shop chỉ lên đơn khi đủ thông tin || 1 | Quyết định từ chối đúng, không lộ thông tin khách khác và có giải thích. |

Câu O1, O2, O5 qua mọi metric áp dụng. O3 trượt `hoi_mot_lan_du_y` (điểm 0 giữ nguyên). O4 trượt cả ba metric code áp dụng.

`quy_doi_dia_chi_dung` trên O3 vẫn là 1: expected là HỎI LẠI và dòng đầu là `QUYẾT ĐỊNH: HỎI LẠI`. Việc nêu đủ phường Bàn Cờ và phường Xuân Hòa, và không hỏi lại sđt đã có, nằm ở `hoi_mot_lan_du_y`. Cách hiểu chung ghi ở `eval/README.md` mục 3.
