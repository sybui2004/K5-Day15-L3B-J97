# Tóm tắt mô phỏng simulate-1@20261128-030455

Do `python run.py simulate` sinh ra — không sửa tay. Chép bảng sang `cost/cost-estimate.md`.

| Persona | Số phiên mô phỏng | Lượt hỏi / phiên | Token vào / phiên | Token ra / phiên | Gọi model / phiên | Gọi công cụ / phiên |
|---|---:|---:|---:|---:|---:|---:|
| shop_nho | 14 | 2 | 4696 | 360 | 4.0 | 6.0 |
| shop_vua | 25 | 3 | 7072 | 535 | 6.0 | 9.0 |
| shop_lon | 11 | 1 | 2333 | 177 | 2.0 | 3.5 |

Tỉ lệ đạt dùng để tính: 28/30 (93%) — lượt run-5@20261128-021955

- Tỉ lệ đạt lấy từ lượt nhóm chọn: eval/run-5.csv (--rate-from).

| Model (giá) | Chi phí / phiên | Chi phí / task thành công | Chi phí / câu hỏi đạt | Chi phí / tháng — thấp (580 người) | Chi phí / tháng — cơ sở (1.741 người) | Chi phí / tháng — cao (5.803 người) | Chi phí / người / tháng (cơ sở) |
|---|---:|---:|---:|---:|---:|---:|---:|
| claude-haiku-5-5 (vào 0.1 · ra 0.5 $/1M) | $0.00074 | $0.00079 | $0.00035 | $167.91 | $504.03 | $1,679.99 | $0.2895 |
| claude-sonnet-5-5 (vào 2.0 · ra 10.0 $/1M) | $0.0148 | $0.0159 | $0.0070 | $3,358.25 | $10,080.53 | $33,599.82 | $5.79 |
| claude-opus-5-5 (vào 4.0 · ra 20.0 $/1M) | $0.0296 | $0.0317 | $0.0139 | $6,716.49 | $20,161.05 | $67,199.65 | $11.58 |

- Chi phí / task thành công = chi phí / phiên ÷ tỉ lệ đạt. Chi phí / câu hỏi đạt = chi phí / phiên ÷ số lượt hỏi trung bình mỗi phiên (2.3) ÷ tỉ lệ đạt — tỉ lệ đạt đo theo từng câu thử.
- Token đo trên model: claude-sonnet-5-5. Giá tính theo từng model trong bảng — model khác bộ tách token thì số token thật có thể lệch; ghi rõ "đo trên model X, tính giá model Y" trong cost/cost-estimate.md.
- Phiên lỗi (không tính vào trung bình): 0/50.
