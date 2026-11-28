# Chi phí khi dùng thật

> Điền ở guide bước 4.2, nộp ở CP4 14:30 Thứ Bảy 28/11. Ôn lại: ngày 13, ngày 1, ngày 14 · lab ngày 13, lab ngày 14. Chấm ở rubric R6.
> Số **không điền tay**: điền `cost/personas.yaml` → `python run.py simulate` → chép bảng trong `cost/simulate-N-summary.md` vào đây.
> Lúc build dùng gói miễn phí vẫn tính theo **giá gói trả phí** — đây là chi phí cho lúc đưa vào dùng thật.

## 1. Đầu vào

- **Persona** (`cost/personas.yaml`): 3 kiểu shop, lấy từ bảng "Số lần / tháng của từng kiểu người dùng" ở `spec.md` §2 (phỏng vấn P1–P4, n = 4). Một phiên = một đơn chốt qua tin nhắn.

  | Kiểu | Tỉ trọng | Đơn / shop / tháng | Lượt hỏi / phiên | Nguồn |
  |---|---:|---:|---:|---|
  | `shop_nho` | 25% | 260 | 2 | P4 (câu 2, câu 4) |
  | `shop_vua` | 50% | 400 | 3 | P1 480, P3 320 → trung bình (câu 2, câu 4) |
  | `shop_lon` | 25% | 650 | 1 | P2 (câu 2, câu 4) |

  Tỉ trọng theo tỉ lệ trong 4 shop đã hỏi *(tự ước tính: chưa có số cả thị trường)*. Lượt hỏi / phiên = 1 + số lần hỏi lại, quy từ số lượt nhắn mỗi đơn (P1 5 · P2 3 · P3 6 · P4 4): đơn trôi chảy 3 lượt, mỗi lần hỏi lại thêm 2 lượt, làm tròn lên *(tự ước tính)*.
- **Số người dùng thật** (số shop dùng sản phẩm) 3 kịch bản: thấp **580** · cơ sở **1.741** · cao **5.803**. Nguồn: tích của bốn thừa số dưới đây. 11.606 chỉ là mốc tham chiếu, **không** phải số shop dùng sản phẩm.

  | Thừa số | Thấp | Cơ sở | Cao | Nguồn |
  |---|---:|---:|---:|---|
  | Quy mô tham chiếu: người nộp thuế kinh doanh TMĐT Cục Thuế TP.HCM đưa vào quản lý, luỹ kế đến hết 10/2024 | 11.606 | 11.606 | 11.606 | [Thanh Niên 04/12/2024](https://thanhnien.vn/doanh-nghiep-ca-nhan-kinh-doanh-thuong-mai-dien-tu-can-luu-y-thue-185241203172338583.htm), xem 27/11/2026 |
  | Hệ số phủ: thêm người bán chưa đăng ký thuế | 1 | 1 | 2 | *(tự ước tính)* |
  | Tỉ lệ thuộc lát cắt: tự chốt đơn qua tin nhắn rồi tạo vận đơn (spec §1) | 0,5 | 0,5 | 0,5 | *(tự ước tính)*: bài báo không tách người bán qua mạng xã hội |
  | Tỉ lệ sử dụng: shop thuộc lát cắt dùng công cụ | 0,1 | 0,3 | 0,5 | *(tự ước tính)* |
  | **Số shop dùng** (làm tròn) | **580** | **1.741** | **5.803** | tích các dòng trên |

  Cả ba kịch bản, kể cả cơ sở, dựa trên ba tỉ lệ chưa đo.
- **Giá** 3 mức model, USD / 1 triệu token vào · ra (`further-reading/model-prices.md` của repo đề, BTC xem https://platform.claude.com/docs/en/about-claude/pricing ngày 25/11/2026): `claude-haiku-5-5` 0,10 · 0,50 · `claude-sonnet-5-5` 2,00 · 10,00 · `claude-opus-5-5` 4,00 · 20,00
- **Tỉ lệ đạt** dùng để tính: 28/30 (93%) — lượt `run-5@20261128-021955` (lượt 2)
- Đo token trên model `claude-sonnet-5-5` (model nhóm chạy eval), tính giá model `claude-haiku-5-5` và `claude-opus-5-5`

## 2. Kết quả mô phỏng

Lượt mô phỏng: `cost/simulate-1.csv` · run ID `simulate-1@20261128-030455` · 50 phiên · seed 42 · 0/50 phiên lỗi. Trace: `traces/simulate-1.jsonl`.

Chạy với `GUARD=nemo` (mặc định của bản chạy thử): mỗi lượt hỏi gọi model 2 lần (lớp chặn NeMo + đọc hội thoại), nên token đã gồm cả lớp chặn.

| Persona | Số phiên mô phỏng | Lượt hỏi / phiên | Token vào / phiên | Token ra / phiên | Gọi model / phiên | Gọi công cụ / phiên |
|---|---:|---:|---:|---:|---:|---:|
| shop_nho | 14 | 2 | 4696 | 360 | 4.0 | 6.0 |
| shop_vua | 25 | 3 | 7072 | 535 | 6.0 | 9.0 |
| shop_lon | 11 | 1 | 2333 | 177 | 2.0 | 3.5 |

| Model | Chi phí / phiên | Chi phí / task thành công | / tháng — thấp (580) | / tháng — cơ sở (1.741) | / tháng — cao (5.803) | / người / tháng (cơ sở) |
|---|---:|---:|---:|---:|---:|---:|
| claude-haiku-5-5 | $0.00074 | $0.00079 | $167.91 | $504.03 | $1,679.99 | $0.2895 |
| claude-sonnet-5-5 | $0.0148 | $0.0159 | $3,358.25 | $10,080.53 | $33,599.82 | $5.79 |
| claude-opus-5-5 | $0.0296 | $0.0317 | $6,716.49 | $20,161.05 | $67,199.65 | $11.58 |

Chi phí / task thành công = chi phí trung bình mỗi phiên ÷ tỉ lệ đạt — **không coi như đạt 100%**.

Hai giả định của dòng Haiku và Opus: (1) token đo trên Sonnet 5.5, chỉ đổi đơn giá; bộ tách token khác thì số thật có thể lệch. (2) Cột "chi phí / task thành công" dùng tỉ lệ đạt 28/30 của Sonnet (`run-5`); nhóm **chưa chạy eval** trên Haiku hay Opus.

Giới hạn của mô phỏng: `simulate.py` không nối các lượt; mỗi lượt lấy ngẫu nhiên một câu `thuong` hoặc `kho` trong `eval/benchmark.csv`. Câu luồng B đã chứa cả hội thoại dài nên token vẫn sát.

## 3. So với impact

Tỷ giá: **26.030 đ / USD** (Vietcombank, bán ra, niêm yết 05:42 ngày 28/11/2026, https://chogia.vn/ty-gia/vietcombank/ · xem 28/11/2026).

- Impact / người / tháng (`spec.md` §2), tức phần **đang mất** ở mỗi shop: phí ship vì chép sai 195.000–494.000đ ÷ 4 shop ≈ **48.750–123.500đ** (đầu trên *(tự ước tính)*) và ≈ **214 phút** đổi địa chỉ cũ (855 ÷ 4). Nhóm **chưa đo** AI tránh được bao nhiêu phần trong đó, nên không ghi "tiết kiệm được" số này.
- Chi phí / người / tháng (cơ sở), quy ra VND:

  | Model | Chi phí / shop / tháng | f\* nếu đang mất 48.750đ | f\* nếu đang mất 123.500đ |
  |---|---:|---:|---:|
  | claude-haiku-5-5 | $0.2895 ≈ 7.500đ | 15% | 6% |
  | claude-sonnet-5-5 | $5.79 ≈ 150.700đ | 309% (không đủ bù) | 122% (không đủ bù) |
  | claude-opus-5-5 | $11.58 ≈ 301.400đ | 618% (không đủ bù) | 244% (không đủ bù) |

  f\* = chi phí / shop / tháng ÷ phí ship đang mất: tỉ lệ phí ship AI phải giúp tránh để hoà vốn. f\* > 100% nghĩa là riêng phí ship không đủ bù, kể cả tránh hết lỗi.
- **Kết luận một dòng — đáng làm không:** với Sonnet 5.5 (model đang chạy), riêng phí ship không đủ bù (f\* 122–309%), phải tính thêm ≈ 214 phút / shop / tháng đổi địa chỉ cũ mới có thể đáng; với Haiku 5.5 chỉ cần tránh 6–15% phí ship đang mất, **nếu** Haiku đạt tỉ lệ như Sonnet. Kết luận phụ thuộc ba số chưa đo: tỉ lệ lỗi AI tránh được, tỉ lệ đạt eval của Haiku, và ba tỉ lệ tự ước tính của số shop. **Nhóm chốt: iterate** (28/11) — giữ lát cắt và ba tỉ lệ tự ước tính hiện tại; trước khi go phải chạy eval trên Haiku và đo tỉ lệ lỗi AI tránh được.

## 4. Độ nhạy và chi phí ngoài model

- **Đổi model** là cần gạt lớn nhất: Sonnet → Haiku giảm chi phí khoảng 20 lần ($5.79 → $0.29 / shop / tháng), Sonnet → Opus gấp đôi.
- **Lớp chặn NeMo** gấp đôi số lần gọi model mỗi lượt. `GUARD=tat` giảm số lần gọi nhưng bỏ một lớp chặn tấn công; nhóm chưa đo token riêng của lớp chặn.
- **Số shop dùng** chỉ nhân chi phí tháng, không đổi chi phí / shop / tháng và f\*.
- **Chi phí ngoài model** chưa tính: hosting, lưu trữ nhật ký, giờ công chủ shop duyệt từng đơn nháp.
