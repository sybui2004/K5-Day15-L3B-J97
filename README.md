> Giờ, mốc, luật, rubric: xem `README.md`, `02-guide.md`, `03-rubric.md` trong repo đề (bộ đề BTC phát).

# J97 — Lên đơn từ tin nhắn chốt mua, quy địa chỉ cũ sang phường/xã mới

**Thành viên, lớp, track:** xem [TEAMS.md](TEAMS.md). **Điền TEAMS.md đúng format**: khi chấm và đánh giá, BTC quét file này để ghép điểm cho từng người.

**Lát cắt:** một chủ shop bán lẻ · khách đã đồng ý mua qua tin nhắn Facebook hoặc website · AI xác định thông tin nhận hàng, kể cả quy địa chỉ cũ sang phường/xã mới theo Nghị quyết 1685/NQ-UBTVQH15, đã đủ và chắc để tạo đơn nháp, hay phải hỏi lại khách · chủ shop nhận đơn nháp chờ duyệt. Chi tiết: [spec.md](spec.md) §4.

---

## Nhóm làm gì, khung làm gì

| Nhóm quyết định và viết | Khung làm sẵn (không cần sửa) |
|---|---|
| Người dùng, pain, bằng chứng, impact (`evidence/`, `spec.md` §1–§2) | — |
| Hình dạng giải pháp, công cụ, prompt, luồng (`spec.md` §4, `codebase/agent.py`, `tools.py`, `ai.py`) | Ghi mọi lần gọi model / công cụ vào trace, cộng token (`codebase/tracing.py`) |
| Bộ câu thử, metric, chuẩn "đạt" (`eval/benchmark.csv`, `eval/metric_spec.yaml`, `spec.md` §7) | Kiểm đủ cột, đủ câu `kho` / `tu_choi`, đủ ≥1/3 câu từ người dùng / data thật (`run.py check`) |
| Chấm cột `pass` theo metric spec | Chạy cả bộ một lệnh, có run ID, model, token từng câu (`run.py eval`) · tính % đạt (`run.py score`) |
| Persona, số người dùng thật, giá model (`cost/personas.yaml`) | Sinh ~50 phiên, chạy thật qua bản chạy thử, tính chi phí / phiên, / task thành công, / tháng 3 kịch bản (`run.py simulate`) |

*Ở J97:* nhóm viết 5 công cụ kiểm sđt, quy đổi và tra phường/xã, tạo đơn nháp, đọc lịch sử khách (`codebase/tools.py`); luồng "model đọc hội thoại trả JSON → code kiểm từng trường → TẠO ĐƠN NHÁP / HỎI LẠI / TỪ CHỐI" (`codebase/agent.py`); 30 câu thử, 5 metric; persona theo số đơn của 4 chủ shop đã phỏng vấn.

## Chạy bản chạy thử của nhóm J97

```bash
python -m pip install -r requirements.txt   # SDK anthropic + nemoguardrails, chỉ cần khi gọi model thật
cp .env.example .env                        # Windows: copy .env.example .env
#   điền API_KEY; nhóm chạy với MODEL_PROVIDER=anthropic, MODEL_NAME=claude-sonnet-5-5, MODEL_EFFORT=low
python run.py                               # mở màn hình duyệt ở http://127.0.0.1:8000
```

- **Màn hình duyệt** (`codebase/web.py`): hộp thư 10 hội thoại mẫu (`data/hop-thu-mau.jsonl`). Bấm từng hội thoại để xem đơn nháp, sửa trường, Duyệt hoặc Huỷ; hội thoại đang chờ khách thì dán câu trả lời của khách để chạy lại (luồng B). Chỉ mở trên máy này (`127.0.0.1`).
- **Lần đầu mở web phải chờ khoảng 1 phút:** trước khi mở cổng, bản chạy thử gọi model cho cả 10 hội thoại (khoảng 6 giây / hội thoại với model thật). Terminal in `Màn hình duyệt — đang xử lý 10 hội thoại…` rồi `Mở trình duyệt: http://127.0.0.1:8000`; thoát bằng Ctrl+C.
- **Hội thoại mới khi demo** (nút *Hội thoại mới* góc phải trên, `POST /api/moi`): gõ hoặc dán đoạn chat, mỗi dòng một tin, dòng bắt đầu `Shop:` là tin của shop; có 5 nút điền nhanh (đủ thông tin, phường cũ bị tách, SĐT thiếu số, đổi người nhận, câu lừa AI). AI chạy ngay, hội thoại lên đầu hộp thư với mã `HT-M01`, `HT-M02`… Mỗi lần chạy AI giữ trace: các bước model / công cụ, token, thời gian, chi phí theo giá trong `cost/personas.yaml` (model chưa có giá thì chỉ hiện token). Khung **AI đã làm gì** ở giữa màn hình hiện từng bước đó; khung bên phải liệt kê **vì sao AI chưa lên đơn**; đầu trang cộng token và chi phí của cả phiên demo; tab **Nhật ký** đọc lại nhật ký duyệt và các lần chạy.
- **Nhật ký duyệt và lần chạy AI:** mặc định ghi `data/nhat-ky-duyet.jsonl` và `data/lan-chay-web.jsonl` (không commit). Muốn lưu vào **Postgres** (tuỳ chọn): `python -m pip install "psycopg[binary]"`, điền `DATABASE_URL` trong `.env` (vd `postgresql://user:pass@127.0.0.1:5432/j97`); bảng tự tạo khi mở màn hình. Postgres không kết nối được thì màn hình báo rồi ghi file, demo vẫn chạy. Xem lại: `GET /api/nhat-ky`.
- **Lớp chặn đầu vào (`GUARD=nemo`, mặc định):** NeMo Guardrails gọi model một lần để kiểm lời khách trước. NeMo cho qua thì model chính đọc tiếp cả hội thoại, nên hội thoại đó tốn 2 lần gọi; NeMo chặn thì trả TỪ CHỐI ngay, bỏ qua lời gọi model chính (1 lần). Vì vậy lần đầu mở web gọi model tối đa 20 lần thay vì 10 và chờ lâu hơn. Chưa cài `nemoguardrails` thì lớp chặn tự bỏ qua và ghi vào trace; muốn tắt hẳn thì đặt `GUARD=tat` trong `.env`. Lớp chặn không tải gì từ mạng ngoài lần gọi model.
- **Bản dòng lệnh dự phòng:** `python codebase/app.py`, gõ một hội thoại, nhận QUYẾT ĐỊNH (TẠO ĐƠN NHÁP / HỎI LẠI / TỪ CHỐI).
- **Chưa có `.env`:** chạy chế độ giả (model giả, không cần `pip install`). Luồng vẫn đi hết, nhưng model giả không trả JSON nên mọi hội thoại ra HỎI LẠI.
- Chạy bộ câu thử, chấm, mô phỏng chi phí: xem mục "Lệnh" bên dưới.

## Chạy trong 3 phút

Bộ khung cần **Python 3.10 trở lên** (Python 3.9 có sẵn trên macOS vẫn chạy được, chỉ in một dòng nhắc). **Chế độ giả không cần `pip install`**; gọi model thật cần `python -m pip install -r requirements.txt` (SDK `anthropic`), thiếu thì báo `ModuleNotFoundError: No module named 'anthropic'`.

**Bước 1 — Mở cửa sổ lệnh ngay trong thư mục repo**

| Windows (PowerShell) | macOS |
|---|---|
| Mở thư mục repo bằng File Explorer → bấm vào thanh địa chỉ → gõ `powershell` → Enter | Mở **Terminal** (Cmd + Space, gõ "Terminal") → gõ `cd ` (có dấu cách) → kéo thả thư mục repo vào → Enter |

Gõ `dir` (Windows) hoặc `ls` (macOS / Linux): thấy `run.py` và `README.md` là đang đứng đúng chỗ.

**Bước 2 — Kiểm Python và chạy thử**

| Việc | Windows (PowerShell) | macOS / Linux |
|---|---|---|
| Kiểm Python | `python --version` (không được thì `py --version`) | `python3 --version` |
| Chạy bản chạy thử (chế độ giả, chưa gọi model) → mở http://127.0.0.1:8000 | `python run.py` | `python3 run.py` |
| Kiểm bộ câu thử | `python run.py check` | `python3 run.py check` |
| Tạo file `.env` để nối model | `copy .env.example .env` | `cp .env.example .env` |

- Windows: gõ `python` mà mở Microsoft Store hoặc báo không có lệnh → dùng `py`. Chưa có Python: cài từ python.org, **tick "Add python.exe to PATH"**, mở lại PowerShell.
- macOS: báo `command not found: python` là bình thường → dùng `python3`.
- `python run.py` in ra `Mở trình duyệt: http://127.0.0.1:8000` là chạy đúng: mở link đó trong trình duyệt, thoát bằng Ctrl+C. Nối model thật: [docs/connect-model.md](docs/connect-model.md).

Trong README này lệnh viết là `python …`; máy nhóm cần `python3` hay `py` thì gõ thay.

## Lệnh

| Lệnh | Làm gì |
|---|---|
| `python run.py` | Mở màn hình duyệt (web http://127.0.0.1:8000, hộp thư 10 hội thoại mẫu). Bản dòng lệnh (gõ đầu vào, nhận kết quả, kèm số lần gọi model / token): `python codebase/app.py` |
| `python run.py check` | Kiểm `eval/benchmark.csv` (6 cột, số câu, `kho` / `tu_choi`, mã `source`, ô trống, dòng mẫu) `eval/metric_spec.yaml` (≥3 metric điền đủ) và `TEAMS.md` (đúng format để BTC quét). Chỉ cảnh báo, không sửa file |
| `python run.py eval --try` | **Thử nối model:** chạy 3 câu đầu (`--try 5` = 5 câu) → `eval/run-try.csv`. Thấy "Nối model được" là xong. Không tính là một lượt |
| `python run.py eval` | Chạy cả bộ qua `codebase/agent.py` → `eval/run-1.csv` (lần sau `run-2.csv`…) + `traces/run-1.jsonl`. Mỗi dòng có run ID, model, số lần gọi model / công cụ, token. Model còn giả → chỉ ghi `run-mock.csv`; mọi câu lỗi → `run-error.csv`; Ctrl+C → `run-stopped.csv` — đều **không** được đánh số |
| `python run.py eval --fake` | Thử riêng bộ chạy, không gọi agent → `eval/run-fake.csv` |
| `python run.py score eval/run-1.csv` | Sau khi điền cột `pass` (1 / 0): in % đạt tổng và theo `type`. Còn ô trống → "CHƯA CHẤM XONG", không in % |
| `python run.py simulate --try` | Thử mô phỏng chi phí 10 phiên (làm trước CP3) → `cost/simulate-try.csv` |
| `python run.py simulate` | Mô phỏng chi phí khi dùng thật theo `cost/personas.yaml` (≥50 phiên) → `cost/simulate-N.csv` + `cost/simulate-N-summary.md` |
| `python run.py simulate --rate-from eval/run-2.csv` | Như trên, lấy tỉ lệ đạt từ đúng lượt chỉ định. Không ghi thì khung lấy lượt `run-N` mới nhất đã chấm, cùng model, và ghi rõ đã lấy lượt nào trong bản tóm tắt |

Gói miễn phí báo hết lượt: thêm `--wait 4` sau `eval` hoặc `simulate` (nghỉ 4 giây giữa hai lượt gọi). Sửa CSV bằng Excel: *File → Save As → CSV UTF-8*; Google Sheets: *Tệp → Tải xuống → CSV*.

**Lượt có lỗi kỹ thuật** (cột `error` có chữ): không sửa tay file đó, chạy lại thành lượt mới và ghi vào bảng các lượt ở `eval/README.md`. Không xoá file lượt nào.

Nhóm dùng stack khác (Node, Streamlit, notebook…): sửa hàm `run_app()` trong `run.py` để `python run.py` vẫn chạy được bản chạy thử, và giữ `answer()` trong `codebase/agent.py` để `eval`, `simulate` chạy được.

## Bản chạy thử — viết ở đâu

| File | Viết gì | Bước guide |
|---|---|---|
| `codebase/agent.py` | `answer(text)` — luồng chính, đúng hình dạng ở `spec.md` §4: workflow 3 bước (model đọc hội thoại → code kiểm → TẠO ĐƠN NHÁP / HỎI LẠI / TỪ CHỐI) | 3.2 |
| `codebase/tools.py` | Công cụ của bài toán, mỗi công cụ một hàm có `@tool` | 2.2, 3.2 |
| `codebase/ai.py` | `call_model(system, user)` — chỗ duy nhất gọi model. Chưa điền `.env` thì chạy **chế độ giả** | 3.3 |
| `codebase/inbox.py` | *(J97)* luồng A: chạy cả hộp thư, xếp TẠO ĐƠN NHÁP → HỎI LẠI → TỪ CHỐI | 3.2 |
| `codebase/web.py` | *(J97)* luồng D + B: màn hình duyệt, sửa trường thì code kiểm lại, hỏi lại nhiều lượt | 3.2 |

- **Hiện tại (CP3):** đã nối Claude (`claude-sonnet-5-5`); `.env` trống thì vẫn chạy chế độ giả để thử luồng.
- Trước mỗi lượt đánh giá: `python run.py eval --try` thấy token > 0 rồi mới `python run.py eval`.
- Bộ chạy gửi **nguyên ô `input`** của câu thử vào `answer(text)`. Dữ liệu nền (bài học, thông báo, lịch…) để trong `data/`, đọc qua công cụ.

## Phần nào thật, phần nào giả

| Thành phần | Thật / Giả | Ghi chú |
|---|---|---|
| Lời gọi AI ở quyết định trung tâm | **Thật** (bắt buộc từ CP3) | Model: `claude-sonnet-5-5`, `MODEL_EFFORT=low`, qua SDK `anthropic` (`codebase/ai.py`). Mỗi hội thoại gọi model 1 lần: đọc hội thoại, trả JSON. Chưa có `.env` thì chạy chế độ giả |
| Kiểm sđt, quy đổi và tra phường/xã | **Thật** | Code, không dùng AI: `validate_phone`, `convert_old_address`, `lookup_address` (`codebase/tools.py`) trên bảng dựng từ Nghị quyết 1685/NQ-UBTVQH15 (`data/chuyen-doi-dia-gioi.csv`) |
| Lịch sử khách cũ (luồng C) | Thật, dữ liệu dựng | `get_customer_history` đọc `data/lich-su-khach.csv`: 6 khách tự dựng, không phải khách thật |
| Hộp thư, màn hình duyệt | Thật, dữ liệu dựng | `data/hop-thu-mau.jsonl`: 10 hội thoại tự dựng. Duyệt chỉ đổi trạng thái đơn trên máy, không lưu vào hệ thống bán hàng nào |
| Tạo đơn, vận đơn GHN | **Giả** | `create_draft_order` chỉ tạo đơn nháp; mã vận đơn `GHN-NHAP-…` là mã giả, **không gọi API GHN**, không bàn giao đơn thật |
| Gửi tin cho khách | **Giả** | Tin hỏi lại chỉ hiện để chủ shop bấm Chép, **không gửi Facebook / website** |
| Bộ câu thử | Thật + dựng | 30 câu: 3 từ chat thật đã che (P2–P4), 7 trích nguồn công khai (3 địa chỉ ví dụ trên since98.vn, 4 review app GHN), 20 tự viết (`data/DATA_CARD.md`) |

## Dùng AI vào việc gì

2–3 dòng (bắt buộc): nhóm dùng công cụ AI nào để làm gì, người kiểm lại phần nào. Chi tiết: [docs/ai-usage.md](docs/ai-usage.md). Coding agent đọc [AGENTS.md](AGENTS.md).

- **Claude Code** (Sỹ, Việt Anh): viết code luồng chính, hộp thư, luồng khách cũ; soạn data tự dựng (`hop-thu-mau.jsonl`, `lich-su-khach.csv`); viết các mục spec và README. Mọi PR có người cặp kia duyệt, 119 test chạy trước khi merge.
- **ChatGPT** (Việt Anh, task Y1): chạy tay đoạn chat chốt đơn để tìm lỗi trước khi viết tiêu chí chấm. Chấm `pass` bằng code (`eval/grade.py`), không dùng LLM.
- Số liệu, trích dẫn phỏng vấn không do AI tạo. Phần của Hưng, An: *chờ xác nhận*.

## File mẫu — điền ở bước nào

| File | Điền ở bước guide | Mốc |
|---|---|---|
| `TEAMS.md` | 1.0 | CP1 · **đúng format**, BTC quét khi chấm |
| `canvas.md` | 1.4 | CP1, cập nhật CP2 |
| `evidence/hypothesis.md` | 1.1 | trước khi tìm bằng chứng |
| `evidence/data-mining.md` · `evidence/interviews/TEMPLATE.md` → `P1.md`… · `evidence/survey/TEMPLATE.md` | 1.2 | bắt đầu sau Zoom, xong CP3 |
| `evidence/summary.md` | 1.2 | CP3 |
| `spec.md` | §0–§2: 1.1–1.3 · §3–§5: 2.1–2.3 · §7: 2.4 · §8: 4.2 · §10: suốt | §7 chốt CP2 · §0–§7 CP3 · đủ CP4 |
| `data/DATA_CARD.md` | 2.4 | bản đầu CP2 |
| `eval/benchmark.csv` · `eval/metric_spec.yaml` | 2.4 | ≥10 câu + metric chốt CP2 · 20–30 câu CP3 |
| `codebase/` | 3.2, 3.3 | khung CP2 · AI thật CP3 |
| `eval/report.md` · `eval/README.md` | 4.1 (README mục 1–4 từ 2.4) | CP4 |
| `cost/personas.yaml` · `cost/cost-estimate.md` | 4.2 | thử 10 phiên CP3 · đủ CP4 |
| `validation/log.md` *(bonus)* | 4.3 | CP4 |
| `slides/outline.md` → `demo-slides.pdf` | 5.1 | CP4 |
| `reflection/TEMPLATE.md` → `reflection/<ten>.md` | 5.3 | 23:59 Thứ Bảy 28/11 |
| `AGENTS.md` · `docs/ai-usage.md` | khi dùng coding agent / AI | suốt |

## Bảy hạng mục bắt buộc — nằm ở file nào

| # | Hạng mục | File |
|---|---|---|
| 1 | Bằng chứng pain | `evidence/` (tổng hợp ở `evidence/summary.md`) |
| 2 | Impact có số | `spec.md` §2 |
| 3 | Thiết kế giải pháp | `spec.md` §4 |
| 4 | Bản chạy thử làm trọn lát cắt | `codebase/` · lệnh ở mục "Lệnh" |
| 5 | Định nghĩa "tốt" + bộ câu thử | `data/DATA_CARD.md` · `eval/` |
| 6 | Mô phỏng chi phí khi dùng thật | `cost/` |
| 7 | Slide + demo + video dự phòng | `demo-slides.pdf` ở thư mục gốc · link video (34 giây, màn hình duyệt chạy `claude-sonnet-5-5`): https://drive.google.com/file/d/1MWRXzBWJ2ZgzxyQcHus2Ad6dGNtcgOx9/view?usp=sharing · log trong video ghi cổng 8010, `web.py` mặc định 8000 |
| + | *Bonus:* người dùng thử | `validation/log.md` |
