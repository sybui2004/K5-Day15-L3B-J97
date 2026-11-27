# Khai báo dùng AI

README của nhóm có mục "Dùng AI vào việc gì" (2–3 dòng, bắt buộc). Ghi chi tiết vào bảng dưới đây.

> Luật của đề: dùng AI để làm bài thoải mái, nhưng **ai không giải thích được phần có tên mình thì phần đó nhận 0 điểm**. Khai thiếu không bị trừ; giấu mới bị.

| Việc | Công cụ AI | AI làm gì | Người kiểm/sửa gì | Ai phụ trách |
|---|---|---|---|---|
| Code bản chạy thử | Claude Code (Sỹ) · Claude Code (Việt Anh, luồng C) · **Hưng, An: chờ xác nhận** | Sỹ: luồng chính `agent.py`, hộp thư `inbox.py`, nối model `ai.py` (*chờ Sỹ xác nhận mức AI viết*). Việt Anh: luồng C (`get_customer_history`, bước 3 trong `agent.py`) | Mỗi PR có người cặp kia duyệt; `python -m unittest discover -s tests` (119 test) chạy trước khi merge | Sỹ, Việt Anh · Hưng (`tools.py`, `web.py`), An (`eval/grade.py`): **chờ xác nhận** |
| Prompt / thiết kế lời gọi mô hình | **Chờ Sỹ xác nhận** | `SYSTEM` trong `codebase/agent.py`: model chỉ đọc hội thoại, trả JSON; code kiểm từng trường | Prompt có test chống chép câu thử (`test_system_prompt_khong_chep_cau_thu`); chạy thử hộp thư mẫu bằng model thật | Sỹ |
| Đào data (viết script đếm, gợi ý nhãn) | Không dùng | Chưa đếm review GHN (`evidence/data-mining.md` mới viết cách đếm) | — | — |
| Rà câu hỏi phỏng vấn / khảo sát | **Chờ xác nhận** | Chỉ rà câu dẫn dắt | — | — |
| Viết câu thử (benchmark) | ChatGPT (Việt Anh, task Y1) · Claude Code (Sỹ: B29, B30) · **còn lại chờ xác nhận** | Y1: chạy tay đoạn chat chốt đơn qua ChatGPT, ghi lỗi để viết tiêu chí, tìm ra kịch bản "phường cũ bị tách, model chọn sai mà vẫn nói chắc" (§5). B29, B30: Claude Code soạn câu tấn công injection theo thiết kế NeMo | Mỗi câu có `source`; Sỹ duyệt B29, B30 và chạy thử bằng model thật trước khi merge (PR #41) | Việt Anh (Y1), Sỹ (B29, B30) |
| Sinh data `synthetic` (nếu có) | Claude Code (Claude Sonnet 5.5) · Claude Code (Claude Opus 5.5) | `data/hop-thu-mau.jsonl` (10 hội thoại, P1); `data/lich-su-khach.csv` (6 khách, P3). Không lấy từ dữ liệu khách thật | Không có seed (viết theo mô tả task). Hộp thư: chạy thử bằng model thật, 9/10 đúng ý định (`data/hop-thu-mau-chay-thu.json`). Chi tiết `data/DATA_CARD.md` | Sỹ (P1), Việt Anh (P3) |
| Chấm cột `pass` bằng LLM (nếu có) | Không dùng | `eval/grade.py` chấm bằng code; 2 metric loại `nguoi` chấm tay (Việt Anh, An, theo kế hoạch P4) | — | An |
| Slide, văn bản | Claude Code (Sỹ) · **người khác chờ xác nhận** | Spec §0–§3, §3 (Sapo), §6; README; DATA_CARD phần B29, B30; thiết kế và kế hoạch NeMo (`docs/superpowers/`); che thông tin cá nhân trên ảnh chụp `evidence/screenshots/`. Số liệu lấy từ phỏng vấn P1–P4, AI không tự thêm số | Sỹ duyệt từng phần trước khi commit; Hưng review PR #29 (spec §0–§3, §6) | Sỹ |

**Không dùng AI để:** tạo người được phỏng vấn, trích dẫn, câu trả lời khảo sát; sửa kết quả các lượt đã chạy (`eval/run-*.csv`, `cost/simulate-*.csv`, `traces/`).
