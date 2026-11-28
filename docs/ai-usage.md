# Khai báo dùng AI

README của nhóm có mục "Dùng AI vào việc gì" (2–3 dòng, bắt buộc). Ghi chi tiết vào bảng dưới đây.

> Luật của đề: dùng AI để làm bài thoải mái, nhưng **ai không giải thích được phần có tên mình thì phần đó nhận 0 điểm**. Khai thiếu không bị trừ; giấu mới bị.

| Việc | Công cụ AI | AI làm gì | Người kiểm/sửa gì | Ai phụ trách |
|---|---|---|---|---|
| Prompt / thiết kế lời gọi mô hình | Claude | `SYSTEM` trong `codebase/agent.py`: model chỉ đọc hội thoại, trả JSON; code kiểm từng trường | Prompt có test chống chép câu thử (`test_system_prompt_khong_chep_cau_thu`); chạy thử hộp thư mẫu bằng model thật | Sỹ |
| Rà câu hỏi phỏng vấn / khảo sát | Codex | Chỉ rà câu dẫn dắt | Chỉ dùng để rà lại văn phong câu hỏi | Sỹ |
| Viết câu thử (benchmark) | ChatGPT (Việt Anh, task Y1) · Claude Code (Sỹ: B29, B30) | Y1: chạy tay đoạn chat chốt đơn qua ChatGPT, ghi lỗi để viết tiêu chí, tìm ra kịch bản "phường cũ bị tách, model chọn sai mà vẫn nói chắc" (§5). B29, B30: Claude Code soạn câu tấn công injection theo thiết kế NeMo | Mỗi câu có `source`; Sỹ duyệt B29, B30 và chạy thử bằng model thật trước khi merge (PR #41) | Việt Anh (Y1), Sỹ (B29, B30) |
| Thử đoạn 11 của Y1 (KH-011, xin thông tin khách khác) | Codex | 28/11, trong phiên rà soát tài liệu: trả lời đoạn KH-011 sau khi đã đọc tiêu chí chấm; Codex từ chối đưa sđt, địa chỉ khách trước | Ghi riêng dưới bảng kết quả `eval/chay-tay-y1.md`, không chấm mức, không tính vào lượt ChatGPT 27/11 (đoạn 1–10) | Việt Anh (Y1) |

**Không dùng AI để:** tạo người được phỏng vấn, trích dẫn, câu trả lời khảo sát; sửa kết quả các lượt đã chạy (`eval/run-*.csv`, `cost/simulate-*.csv`, `traces/`).
