# Reflection — Đoàn Sỹ Hưng

1. Vai trò + phần mình làm (trỏ tới file / commit):
   Thành viên, cặp X (cùng Sỹ), làm phần bản chạy thử và data địa giới. `TEAMS.md` ghi chung cho cặp X cả sơ đồ `spec.md` §4; sơ đồ do Sỹ vẽ (`1e648e0`), phần của mình là các file dưới đây.
   - Bảng chuyển đổi theo Nghị quyết 1685, `data/chuyen-doi-dia-gioi.csv` (`3dddc3e`, `b765eb6`); đối chiếu tay 29 khoản với văn bản (`data/DATA_CARD.md`).
   - Công cụ kiểm sđt, quy đổi và tra địa giới, tạo đơn nháp, `codebase/tools.py` (`55399df`, `f4f38cc`, `cf07cdf`).
   - Màn hình duyệt và hỏi lại nhiều lượt, `codebase/web.py` (`fb45e7c`, `961d9da`, `f7d24c0`, `d51b276`, `4a665ca`).
   - Câu thử B23–B28 (`cf15ce6`) và demo giao diện `docs/ui-demo/` (`2e404a3`).

2. AI hỗ trợ mình thế nào (việc gì, công cụ gì, chỗ nào phải sửa lại output AI):
   Mình dùng Claude Code cho `tools.py`, `web.py` (kiểm bằng cách đọc lại code) và demo UI (`claude-opus-5-5` viết file HTML, mình mở thử bằng trình duyệt).
   Đọc lại chưa đủ: code vẫn phải sửa sau khi người cặp duyệt PR.
   Review PR #16 chỉ ra `validate_phone` còn nhận chữ số ngoài 0–9, và khách đã ghi tỉnh cũ mà vẫn xét phường của tỉnh khác (sửa ở `f4f38cc`).
   Review PR #26 chỉ ra kết quả về muộn có thể vẽ lại sai hội thoại đang chọn, và phải ghi được nhật ký rồi mới đổi trạng thái đơn (sửa ở `961d9da`).
   Claude Code cũng soạn nháp file này từ lịch sử git và câu trả lời của mình.

3. Một câu thử trượt của nhóm và mình học được gì từ nó:
   B12: khách ghi "3 Lê Văn Sỹ, Phường 1", không ghi quận; chuẩn là chỉ hỏi quận/huyện cũ.
   Lượt 1 (`run-3`) hỏi tỉnh/thành và phường/xã; lượt 2 (`run-5`) đã hỏi quận/huyện cũ nhưng hỏi thêm tỉnh nên vẫn trượt `hoi_mot_lan_du_y` (`eval/report.md`). Cả hai lượt không tạo đơn sai.
   Qua câu này mình nhận ra an toàn (không tạo đơn sai) mới chỉ là một nửa; hỏi thừa hay hỏi lan man vẫn dễ làm khách khó chịu và bỏ ngang. Nên dù chỉ vướng ở một câu hỏi lại, mình thấy vẫn phải đo kỹ cách AI hỏi khách và giữ nguyên `expected` làm chuẩn, chứ không nới tiêu chí để kéo điểm lên.
