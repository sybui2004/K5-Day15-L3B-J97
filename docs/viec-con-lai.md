# Việc còn lại trước hạn 23:59 thứ Bảy 28/11 (giờ VN)

Rà lúc khoảng 18:00 ngày 28/11 trên `develop` (commit `4fb5e80`) và PR #66 đang mở.

| Ai | Việc | Mức | Nên xong trước |
|---|---|---|---|
| An | [1. Người dùng thử](#1-an--người-dùng-thử-validationlogmd) | Bonus, +5 (tổng tối đa vẫn 100) | 22:00 |
| Cả 4 người | [2. Reflection cá nhân](#2-cả-nhóm--reflection-cá-nhân) | **Bắt buộc** | 22:00 |
| Hưng | [3. Xác nhận phần khai AI ở PR #66](#3-hưng--xác-nhận-phần-khai-ai-ở-pr-66) | **Bắt buộc** | 21:00 |
| Sỹ | [4. Gộp bài và kiểm lần cuối](#4-sỹ--gộp-bài-và-kiểm-lần-cuối) | **Bắt buộc** | 23:30 |

Các mốc "nên xong trước" là đề xuất, để còn thời gian review. Hạn của đề là 23:59.

## Luật chung cho mọi việc

- Nhánh mới tách từ `develop`, mở PR vào `develop`.
- Thay đổi sau CP4 ghi một dòng vào `spec.md` §10, bảng sau CP4: giờ · đổi gì · vì sao.
- Không sửa `spec.md` §7, `eval/metric_spec.yaml`, `expected` trong bộ câu thử, và các file kết quả đã chạy (`eval/run-*.csv`, `cost/simulate-*.csv`, `traces/*`).
- Không bịa người thử, người phỏng vấn, trích dẫn hay số liệu. Không commit API key hay dữ liệu cá nhân thật.

## 1. An — Người dùng thử (`validation/log.md`)

File trên `develop` vẫn là mẫu trống.

**Điều kiện được điểm:** ít nhất **2 người ngoài nhóm** đã dùng thử thật (nên có 3). Bạn nhóm khác được tính nếu đúng là người dùng của lát cắt. Đề (guide 4.3) lưu ý: track D thì học viên cũng là người mua online, còn vai chuyên môn phải là người làm nghề thật. Lát cắt của mình dành cho người lên đơn, nên ghi đúng vai thật của người thử, không gọi họ là "chủ shop" nếu họ không phải.

**Không đủ 2 người thật thì để nguyên mẫu trống và báo Sỹ.** Mất phần bonus, còn điền phiên không có thật là bịa số liệu.

### Chuẩn bị

- Chạy màn hình duyệt theo `README.md` và `docs/huong-dan-demo.md`.
- Chỉ dùng dữ liệu mẫu. Người thử không nhập tên, sđt, địa chỉ thật.

### Một phiên, khoảng 10 phút

1. **Làm quen (~1'):** "Tụi mình đánh giá sản phẩm, không đánh giá bạn. Cứ nói to suy nghĩ."
2. **Bối cảnh (~1'):** "Kể lần gần nhất bạn lên đơn từ tin nhắn, bạn đã làm gì?" Chưa từng làm thì ghi rõ là chưa.
3. **Giao việc (~1'):** giao theo kết quả cần đạt, không chỉ nút. Người thử tự cầm chuột.
4. **Quan sát (~5'):** im lặng ghi việc làm đầu tiên, chỗ do dự, chỗ hiểu sai. Người thử kẹt thì chỉ hỏi "Bạn sẽ làm gì tiếp?" hoặc "Bạn nghĩ nó nên chạy thế nào?". Không giải thích, không hỏi "bạn có thích không".
5. **Hỏi sau (~2'):** Điều gì khó hiểu nhất? Bạn có tin kết quả này không, vì sao? Bạn có dùng thật không? Nếu mai không được dùng nữa, bạn thấy rất tiếc, hơi tiếc hay không sao?

Gợi ý việc giao, nội dung tin nhắn lấy ở `docs/huong-dan-demo.md`:

| Ca | Câu giao cho người thử | Để ý |
|---|---|---|
| B04 · phường cũ đổi tên | "Chuẩn bị đơn cho khách này." | Có hiểu và tin phường mới không |
| B09 · phường cũ bị tách | "Xử lý đơn này tới khi lên được." | Có biết mình phải tự gửi câu hỏi cho khách không (đừng nhắc trước) |
| B14 · thiếu sđt, khách giục | "Khách đang giục, bạn xử lý đi." | Sau khi thấy TỪ CHỐI, có biết làm gì tiếp không |

### Ghi vào file

- Mỗi người một dòng, giữ nguyên 5 cột của mẫu: vai · việc giao · quan sát · trích nguyên văn · mức nghiêm trọng (cao / vừa / thấp). Không ghi tên.
- Quan sát là việc người thử đã làm. Trích dẫn là đúng câu họ nói. Ghi ngay trong lúc thử.
- Nên nói rõ mỗi người ở ngoài nhóm và vai thật của họ.
- Toàn lời khen thì phiên chưa đạt: giao việc khó hơn.
- Ghi câu trả lời "rất tiếc / hơi tiếc / không sao" của từng người.
- Điền 4 dòng tổng hợp: chủ đề lặp nhiều nhất · sửa gì trước demo · giữ gì và vì sao · để dành sau. Demo đã qua thì ghi rõ việc nào sửa trước 23:59, việc nào để sau.
- **Bắt buộc để được điểm:** rút ra ít nhất một thay đổi và ghi vào `spec.md` §10, hoặc ghi giữ nguyên kèm lý do. Chỉ ghi là đã sửa khi code đã sửa thật.
- Có dùng AI để soạn hay sửa câu chữ thì khai ở `docs/ai-usage.md`. Dòng "Hưng, An không dùng AI ngoài các việc đã ghi" ở `spec.md` §10 phải còn đúng.

## 2. Cả nhóm — Reflection cá nhân

Thư mục `reflection/` mới có `TEMPLATE.md`, **chưa có file của ai**. Theo rubric, thiếu reflection thì phần việc của người đó bị 0 điểm.

| Người viết | File cần tạo |
|---|---|
| Bùi Thái Sỹ | `reflection/bui-thai-sy.md` |
| Trần Việt Anh | `reflection/tran-viet-anh.md` |
| Đoàn Sỹ Hưng | `reflection/doan-sy-hung.md` |
| Phạm Thanh An | `reflection/pham-thanh-an.md` |

Chép từ `reflection/TEMPLATE.md`, trả lời 3 câu, mỗi câu 3–6 dòng:

1. Vai trò và phần mình làm, trỏ tới file hoặc commit.
2. AI hỗ trợ thế nào: việc gì, công cụ gì, chỗ nào phải sửa lại output của AI. Nội dung phải khớp với `docs/ai-usage.md`.
3. Một câu thử trượt của nhóm và bài học rút ra. Lấy câu từ `eval/report.md`.

Mỗi người tự viết phần của mình và phải giải thích được khi bị hỏi. Phần việc nêu trong file nên khớp với cột "Phần việc chính" ở `TEAMS.md`.

## 3. Hưng — Xác nhận phần khai AI ở PR #66

PR: https://github.com/sybui2004/K5-Day15-L3B-J97/pull/66

Phần demo UI (`docs/ui-demo/`) đang có ghi chú *(chờ Hưng xác nhận)*. Hưng cần trả lời:

- [ ] Công cụ và model đã dùng, AI làm phần nào, Hưng đã kiểm hoặc sửa gì (`docs/ai-usage.md`).
- [ ] Lý do làm demo UI (`spec.md` §10).
- [ ] Ngoài các việc đã khai thì có dùng AI vào việc nào khác không (`README.md`, `spec.md` §10).

Trả lời xong thì cập nhật nội dung và **bỏ hết ghi chú "chờ Hưng xác nhận"** trên nhánh `docs/cp4-sau-demo`.

## 4. Sỹ — Gộp bài và kiểm lần cuối

Điểm lab chấm trên commit cuối trước 23:59.

- [ ] Review và merge PR #66 sau khi Hưng xác nhận.
- [ ] Merge PR của An và các file reflection vào `develop`. Nhiều PR cùng sửa `spec.md` §10, nên cẩn thận khi gỡ conflict.
- [ ] Merge `develop` vào `main`.
- [ ] Trên `main`: `python3 run.py check` và `python3 -m unittest discover -s tests` đều qua.
- [ ] `reflection/` đủ 4 file.
- [ ] Mở link video dự phòng trong README bằng cửa sổ ẩn danh (lần rà này chưa kiểm).
- [ ] Không có API key, `.env` hay dữ liệu cá nhân thật trong repo.
- [ ] Mọi thay đổi sau CP4 có dòng ở `spec.md` §10.
- [ ] Không bắt buộc: `AGENTS.md`, mục "Quy ước của nhóm", còn 3 chỗ trống `__`.

## Đã kiểm trong lần rà này

Trên `develop` tại `4fb5e80`:

- `python3 run.py check`: không thấy vấn đề (30 câu thử, 5 metric, `TEAMS.md` đúng format).
- `python3 -m unittest discover -s tests`: chạy 245 test, kết quả OK, bỏ qua 20.
- Quét một số mẫu API key (`sk-ant-`, `sk-`, `AIza`): không khớp. File tên `.env*` được git theo dõi chỉ có `.env.example`. Lần quét này không kiểm dữ liệu cá nhân.
- Có `demo-slides.pdf` ở thư mục gốc.

Lần rà này không chấm lại chất lượng nội dung các khối R1–R7.
