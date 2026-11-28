# Tài khoản khách, đăng nhập shop, chat HITL — kế hoạch làm

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Người xem demo đăng ký / đăng nhập làm khách và chat với shop trên j97.sunstack.org; bot tự trả lời và lên đơn nháp; shop (`admin`) đăng nhập, duyệt đơn, nhắn khách và tiếp quản cuộc chat.

**Architecture:** Mở rộng `codebase/web.py` (đổi sang `ThreadingHTTPServer`), thêm `codebase/tai_khoan.py` (mật khẩu, phiên, giới hạn tần suất), thêm bảng / file lưu ở `codebase/kho.py`. Mỗi tài khoản khách là một hội thoại `TK-<username>` trong `ManHinh`; tin khách vào hàng đợi, một luồng nền chạy `xu_ly` qua `_khoa_ai` như #59. Giao diện: trang mới `codebase/static/khach.html` + `khach.js`, trang shop thêm cổng đăng nhập và ô nhắn khách.

**Tech Stack:** Python 3 thư viện chuẩn (`http.server`, `hashlib.scrypt`, `secrets`, `hmac`, `ipaddress`, `threading`), `psycopg` (đã có, tuỳ chọn), JavaScript thuần, nginx 1.28 + Docker Compose của PR #61.

**Spec:** `docs/superpowers/specs/2026-11-28-chat-khach-hitl-design.md`

## Global Constraints

- Không thêm gói Python / JS. Không sửa `codebase/tracing.py`, luồng AI (`agent.py`, `guard.py`, `ai.py`, `tools.py`), bộ câu thử, metric, chuẩn "đạt", kết quả các lượt đã chạy.
- Commit đứng tên `sybui2004 <symerline2004@gmail.com>` (`git -c user.name=… -c user.email=…`), không có dòng Co-Authored-By; mô tả PR không có dòng "Generated with".
- Python test: `/project/template-devops/K5-Day15-L3B-J97/.venv/bin/python -m unittest discover -s tests` (gọi là `$PY`). Node ≥ 20 cho Playwright: `~/.nvm/versions/node/v22.23.5/bin/node`.
- Cookie phiên `j97_phien`: `HttpOnly; SameSite=Strict; Path=/; Max-Age=43200`, thêm `Secure` khi yêu cầu HTTPS (§5.2).
- POST giữ `post_hop_le` (header `X-Man-Hinh-Duyet: 1` + JSON). Không script / style nội dòng (CSP `script-src 'self'`).
- Giới hạn (§5.3): đăng ký ≤ 5 / IP / 3600 s; đăng nhập sai ≤ 10 / (IP, username) / 600 s; khách gửi ≤ 5 tin / tài khoản / 60 s; trần chung ≤ 60 tin khách / 60 s; tin ≤ 500 ký tự; ≤ 200 tin / tài khoản. Vượt → HTTP 429 `{"loi": "…", "cho_giay": N}`.
- Username 3–32 ký tự `[a-z0-9_.]` (chuyển chữ thường), cấm `admin`; mật khẩu 6–128 ký tự.
- Câu bot khi TẠO ĐƠN NHÁP (đúng chữ): `Dạ shop đã ghi nhận đơn của anh/chị: {ten} · {sdt} · {dia_chi}, {phuong_xa}, {tinh_thanh} · {san_pham} × {so_luong}. Shop kiểm lại rồi xác nhận ngay ạ.` Không có chuỗi "đã lên đơn". Tin hệ thống khi duyệt: `Đơn {ma_don} đã được shop xác nhận.`
- Trang khách hiện cố định: `Bản demo — đừng nhập tên, số điện thoại, địa chỉ thật.`
- Mọi thay đổi ghi `spec.md` §10.

## Review Focus

1. Khách A đọc / gửi vào cuộc chat của khách B, hoặc gọi API shop → luôn 403 / 401 (test ở Task 3, Task 4).
2. Khách gửi tin liên tục trong lúc AI đang chạy → không mất tin, chỉ một lần chạy AI cho cả loạt, bot trả lời theo tin mới nhất (Task 4: `test_gop_tin_trong_hang_doi`).
3. Shop tiếp quản đúng lúc AI đang chạy → không có tin bot nào xuất hiện sau tin shop (Task 4: `test_tiep_quan_giua_luc_ai_chay`).
4. Máy chủ khởi động lại → đơn đã duyệt vẫn ở trạng thái đã duyệt, phiếu chờ duyệt vẫn còn, không gọi AI (Task 4: `test_dung_lai_sau_khoi_dong`).
5. Header giả `X-Real-IP` / `X-Forwarded-Proto` từ máy không phải proxy tin cậy → bị bỏ qua (Task 3: `test_khong_tin_header_tu_ngoai`).

---

### Task 1: Lưu tài khoản, phiên, tin nhắn, cuộc chat (`kho.py`)

**Files:**
- Modify: `codebase/kho.py`
- Test: `tests/test_kho.py`

**Interfaces:**
- Produces (cả `KhoFile` và `KhoPostgres`):
  - `class TrungTen(ValueError)` (module `kho`)
  - `tao_tai_khoan(username: str, mat_khau_bam: str, vai: str, ip: str) -> int` — trùng username → `TrungTen`
  - `tim_tai_khoan(username: str) -> dict | None` — `{id, username, mat_khau_bam, vai}`
  - `luu_phien(token_bam: str, tai_khoan_id: int, het_han: float) -> None`; `doc_phien(token_bam: str) -> dict | None` — `{tai_khoan_id, username, vai, het_han}`; `xoa_phien(token_bam: str) -> None`
  - `ghi_tin(tai_khoan_id: int, nguoi_noi: str, noi_dung: str) -> dict` — `{id, tai_khoan_id, nguoi_noi, noi_dung, luc}`, `id` tăng dần toàn kho
  - `doc_tin(tai_khoan_id: int, sau_id: int = 0) -> list[dict]` — theo `id` tăng
  - `luu_cuoc_chat(tai_khoan_id: int, d: dict) -> None` (ghi đè; khoá của `d`: `che_do, trang_thai, phien_ban, kq, ma_don, ma_van_don, co_tin_chua_doc, moc_tin_id`); `doc_cac_cuoc_chat() -> list[dict]` (mỗi phần tử thêm `tai_khoan_id`, `username`)
  - `ghi_don_cu(tai_khoan_id: int, d: dict) -> None` (`moc_tin_id, ket_qua, ma_don, truong, luc`); `doc_don_cu(tai_khoan_id: int) -> list[dict]`
- `KhoFile(nhat_ky, lan_chay=None, chat=None)`: tài khoản, phiên, tin, cuộc chat, đơn cũ lưu chung một file JSON `data/chat-khach.json` (ghi lại cả file sau mỗi thay đổi, có `threading.Lock`). Thêm `data/chat-khach.json` vào `.gitignore`.
- `KhoPostgres`: thêm các bảng của spec §5.7 vào `BANG` (`tai_khoan`, `phien_dang_nhap`, `tin_nhan`, `cuoc_chat`, `don_cu`); `kq`, `truong` là `jsonb`.

- [ ] **Step 1: Viết test** trong `tests/test_kho.py`, lớp `TestKhoChat` chạy trên `KhoFile` (thư mục tạm): `test_tai_khoan_trung_ten` (tạo 2 lần `"lan"` → `TrungTen`), `test_phien` (lưu, đọc ra `username`, `vai`; xoá → `None`), `test_tin_theo_thu_tu_va_sau_id` (3 tin, `doc_tin(id, sau_id=tin1["id"])` trả 2 tin), `test_cuoc_chat_va_don_cu_ben_sau_khi_mo_lai` (ghi rồi tạo `KhoFile` mới cùng đường dẫn → đọc lại đúng). Thêm cùng bộ test vào lớp Postgres sẵn có (chỉ chạy khi có `TEST_DATABASE_URL`).
- [ ] **Step 2:** `$PY -m unittest tests.test_kho -v` → các test mới FAIL (thiếu hàm).
- [ ] **Step 3:** Viết các hàm trên trong `KhoFile`, `KhoPostgres`.
- [ ] **Step 4:** `$PY -m unittest tests.test_kho -v` → PASS (lớp Postgres skip nếu không có DB).
- [ ] **Step 5:** Commit `kho: lưu tài khoản, phiên, tin nhắn, cuộc chat khách`.

### Task 2: Mật khẩu, phiên, giới hạn tần suất (`tai_khoan.py`)

**Files:**
- Create: `codebase/tai_khoan.py`
- Test: `tests/test_tai_khoan.py`

**Interfaces:**
- Consumes: Task 1 (`tao_tai_khoan`, `tim_tai_khoan`, `luu_phien`, `doc_phien`, `xoa_phien`, `TrungTen`).
- Produces:
  - `bam_mat_khau(mk: str) -> str` (`"scrypt$<muối hex>$<băm hex>"`, `n=2**14, r=8, p=1, dklen=32`); `kiem_mat_khau(mk: str, bam: str) -> bool` (`hmac.compare_digest`)
  - `class LoiDangNhap(ValueError)`; `class QuaGioiHan(Exception)` có thuộc tính `cho_giay: int`
  - `class GioiHan(so: int, giay: float)` — `dung(khoa: str, bay_gio: float | None = None) -> None` ném `QuaGioiHan`; cửa sổ trượt, an toàn luồng
  - `class QuanLyTaiKhoan(kho, mat_khau_admin: str)` — `dang_ky(username, mat_khau, nhap_lai, ip) -> dict`, `dang_nhap(username, mat_khau, ip) -> dict`, `tao_phien(tk: dict) -> str` (token), `doc_phien(token: str | None) -> dict | None`, `xoa_phien(token: str) -> None`. `tk` = `{id, username, vai}`; admin là `{id: 0, username: "admin", vai: "shop"}`, không lưu trong kho, so với `mat_khau_admin`. Hạn phiên `HET_HAN_PHIEN = 43200`. Token lưu dạng `sha256` hex.
  - Hằng: `GIOI_HAN_DANG_KY = (5, 3600)`, `GIOI_HAN_DANG_NHAP_SAI = (10, 600)`.

- [ ] **Step 1: Viết test** `tests/test_tai_khoan.py`: `test_bam_va_kiem` (đúng → True, sai → False, hai lần băm cùng mật khẩu khác nhau); `test_dang_ky_hop_le_va_chuan_hoa` (`"  Lan.Nguyen "` → `"lan.nguyen"`, vai `"khach"`); `test_dang_ky_sai` (username `"ab"`, `"admin"`, `"lan!"`, mật khẩu `"12345"`, nhập lại khác → `LoiDangNhap`); `test_trung_ten` → `LoiDangNhap`; `test_gioi_han_dang_ky_theo_ip` (5 lần ok, lần 6 cùng IP → `QuaGioiHan` có `cho_giay > 0`, IP khác vẫn ok); `test_dang_nhap_sai_bi_chan` (10 lần sai → lần 11, kể cả đúng mật khẩu → `QuaGioiHan`); `test_admin` (`"admin"`/`mat_khau_admin` → vai `"shop"`, sai → `LoiDangNhap`); `test_phien_het_han` (đặt `het_han` quá khứ → `doc_phien` trả `None`); `test_gioi_han_cua_so_truot` (`GioiHan(2, 10)`: t=0,1 ok, t=2 lỗi, t=11 ok).
- [ ] **Step 2:** `$PY -m unittest tests.test_tai_khoan -v` → FAIL (chưa có module).
- [ ] **Step 3:** Viết `codebase/tai_khoan.py`.
- [ ] **Step 4:** `$PY -m unittest tests.test_tai_khoan -v` → PASS.
- [ ] **Step 5:** Commit `tai_khoan: mật khẩu scrypt, phiên, giới hạn tần suất`.

### Task 3: HTTP — đăng nhập, cookie, IP tin cậy, phân vai (`web.py`)

**Files:**
- Modify: `codebase/web.py` (lớp `MayChu`, `XuLyYeuCau`, `main`)
- Test: `tests/test_web.py` (lớp mới `TestDangNhapHttp`, theo kiểu `TestGioiHanPost` dựng server thật trên cổng tạm)

**Interfaces:**
- Consumes: Task 2 (`QuanLyTaiKhoan`, `QuaGioiHan`, `LoiDangNhap`).
- Produces:
  - `MayChu(ThreadingHTTPServer)` với `daemon_threads = True`.
  - `XuLyYeuCau.tai_khoan: QuanLyTaiKhoan` (gán trong `main`, cạnh `man_hinh`).
  - `TRUSTED_PROXY` = danh sách mạng từ biến môi trường `TRUSTED_PROXY` (vd `172.16.0.0/12`), rỗng khi chạy máy.
  - `ip_khach(handler) -> str` (dùng `X-Real-IP` chỉ khi `handler.client_address[0]` thuộc `TRUSTED_PROXY`); `la_https(handler) -> bool` (`X-Forwarded-Proto == "https"` cùng điều kiện).
  - `XuLyYeuCau._ai_dang_nhap() -> dict | None` (đọc cookie `j97_phien`).
  - Endpoint: `POST /api/dang-ky`, `POST /api/dang-nhap` (cả hai trả `{vai, username}` + `Set-Cookie`), `POST /api/dang-xuat`, `GET /api/toi` (401 nếu chưa đăng nhập).
  - Mọi endpoint shop hiện có (`/api/hop-thu`, `/api/nhat-ky`, `/api/kiem|duyet|huy|tra-loi|moi|nhan-them`) → 401 nếu chưa đăng nhập, 403 nếu vai `khach`.
  - `main()`: `ADMIN_PASSWORD` (mặc định `"admin"`, in cảnh báo nếu mặc định và `HOST != "127.0.0.1"`).

- [ ] **Step 1: Viết test** `TestDangNhapHttp`: `test_chua_dang_nhap_api_shop_401` (GET `/api/hop-thu`, POST `/api/duyet` → 401); `test_khach_goi_api_shop_403`; `test_dang_ky_dat_cookie` (header `Set-Cookie` có `j97_phien=`, `HttpOnly`, `SameSite=Strict`, không có `Secure` khi gọi thẳng); `test_cookie_secure_qua_proxy_tin_cay` (đặt `TRUSTED_PROXY=127.0.0.0/8`, header `X-Forwarded-Proto: https` → có `Secure`); `test_khong_tin_header_tu_ngoai` (`TRUSTED_PROXY` rỗng, gửi `X-Real-IP` khác nhau → vẫn tính chung một IP cho giới hạn đăng ký: lần 6 → 429); `test_admin_dang_nhap_vao_hop_thu` (200); `test_dang_xuat` (sau đó `/api/toi` → 401); `test_dang_ky_qua_gioi_han_429` (body có `cho_giay`). Sửa các test HTTP / ManHinh sẵn có gọi API shop để đăng nhập admin trước (helper `_dang_nhap_admin(conn) -> cookie`).
- [ ] **Step 2:** `$PY -m unittest tests.test_web -v` → test mới FAIL.
- [ ] **Step 3:** Viết phần HTTP trong `web.py`.
- [ ] **Step 4:** `$PY -m unittest discover -s tests` → PASS (trừ test 413 ngẫu nhiên #47).
- [ ] **Step 5:** Commit `web: đăng nhập shop / khách, cookie phiên, IP tin cậy, ThreadingHTTPServer`.

### Task 4: Cuộc chat khách, bot, shop tiếp quản, nhiều đơn (`web.py`)

**Files:**
- Modify: `codebase/web.py` (lớp `ManHinh`, endpoint chat)
- Test: `tests/test_web.py` (lớp mới `TestChatKhach`, model giả `_model_tra` như các test hiện có)

**Interfaces:**
- Consumes: Task 1 (kho), Task 3 (`_ai_dang_nhap`, phân vai), `ManHinh._chay`, `_luu_lan_chay`, `_khoa`, `_khoa_ai`, `kiem_khi_sua`, `create_draft_order` sẵn có.
- Produces (phương thức `ManHinh`):
  - `nap_cuoc_chat() -> None` — lúc khởi động, dựng hội thoại `TK-<username>` từ `kho.doc_cac_cuoc_chat()`, `doc_tin`, `doc_don_cu`; không gọi AI.
  - `khach_gui(tk: dict, tin: str) -> dict` — kiểm độ dài / số tin, ghi `khach`, đưa vào hàng đợi nếu `che_do == "bot"`, ngược lại tăng `phien_ban`, đặt `co_tin_chua_doc = True`. Ném `LoiThaoTac` / `QuaGioiHan`.
  - `khach_doc(tk: dict, sau_id: int) -> dict` — `{"tin": [...], "dang_soan": bool}`; mỗi tin `{id, nguoi_noi, noi_dung, luc}`.
  - `shop_nhan(ma: str, tin: str) -> dict` (phiên) — ghi `shop`, `che_do = "shop"`.
  - `shop_tra_bot(ma: str) -> dict`; `shop_doc_lai(ma: str) -> dict` (chạy `xu_ly` trên văn bản sau mốc, không ghi tin `bot`, xoá `co_tin_chua_doc`).
  - `duyet`, `huy` với hội thoại `nguon == "khach"`: ghi `don_cu`, đặt mốc (`moc_tin_id` = id tin cuối), trả cuộc chat về chờ đơn mới; `duyet` thêm tin `he_thong` theo câu ở Global Constraints. `them_tra_loi` từ chối hội thoại `nguon == "khach"` (khách tự nhắn).
  - Phiên `TK-…` có thêm khoá: `tai_khoan_id, username, che_do, co_tin_chua_doc, moc_tin_id, tin` (toàn bộ tin cho shop), `don_cu`.
  - Hằng: `GIOI_HAN_TIN_TAI_KHOAN = (5, 60)`, `GIOI_HAN_TIN_TOAN_MAY = (60, 60)`, `TIN_TOI_DA_KY_TU = 500`, `TIN_TOI_DA_MOI_TK = 200`.
  - Endpoint: `GET /api/chat?sau=<id>`, `POST /api/chat/gui {tin}` (vai `khach`); `POST /api/shop/nhan {ma, tin}`, `POST /api/shop/tra-bot {ma}`, `POST /api/shop/doc-lai {ma}` (vai `shop`).
- Văn bản đưa AI: `"Mã khách: TK-<username> | " + " | ".join("Khách: …" / "Shop: …")` cho tin sau `moc_tin_id`, bỏ `he_thong`. Một luồng nền `_luong_chat` đọc hàng đợi (tập `tai_khoan_id` chờ, gộp); chạy `xu_ly` qua `_chay` (có `_khoa_ai`), rồi dưới `_khoa`: cập nhật phiên, `phien_ban += 1`, lưu kho, và **chỉ nếu `che_do` vẫn là `"bot"`** ghi tin `bot` (TẠO ĐƠN NHÁP → câu ở Global Constraints; HỎI LẠI / TỪ CHỐI → `tin_gui_khach`). `dang_soan` = tài khoản đang trong hàng đợi hoặc đang chạy.

- [ ] **Step 1: Viết test** `TestChatKhach`: `test_bot_tra_loi_hoi_lai`; `test_tao_don_nhap_khong_hua_len_don` (tin bot chứa `"đã ghi nhận đơn"`, không chứa `"đã lên đơn"`; phiên `cho_duyet`); `test_khach_chi_thay_tin_cua_minh`; `test_gop_tin_trong_hang_doi` (chặn model bằng `threading.Event`, gửi 3 tin → 1 lần chạy AI, 1 tin bot); `test_tiep_quan_giua_luc_ai_chay` (AI đang chạy, `shop_nhan` → không có tin `bot` sau tin `shop`, đơn nháp vẫn cập nhật); `test_che_do_shop_tin_khach_khong_chay_ai_va_phieu_cu` (`phien_ban` tăng, `duyet` với phiên bản cũ → `LoiThaoTac`); `test_tra_bot_chay_tu_tin_ke_tiep`; `test_duyet_them_tin_he_thong_va_mo_don_moi` (sau duyệt, tin khách mới → AI chỉ thấy tin sau mốc, `don_cu` có 1 phần tử); `test_gioi_han_tin` (tin 501 ký tự → lỗi; 6 tin / phút → `QuaGioiHan`); `test_dung_lai_sau_khoi_dong` (ManHinh mới cùng kho → trạng thái `da_duyet` / `cho_duyet` giữ nguyên, model không được gọi); qua HTTP: `test_khach_khong_gui_vao_chat_nguoi_khac` và `test_khach_goi_shop_nhan_403`.
- [ ] **Step 2:** `$PY -m unittest tests.test_web -v` → test mới FAIL.
- [ ] **Step 3:** Viết phần chat trong `ManHinh` và endpoint.
- [ ] **Step 4:** `$PY -m unittest discover -s tests` → PASS.
- [ ] **Step 5:** Commit `web: cuộc chat khách, bot trả lời, shop tiếp quản, nhiều đơn mỗi cuộc chat`.

### Task 5: Trang khách (`khach.html`)

**Files:**
- Create: `codebase/static/khach.html`, `codebase/static/khach.js`
- Modify: `codebase/static/app.css` (lớp dùng chung cho form và bong bóng chat)

**Interfaces:**
- Consumes: Task 3 (`/api/dang-ky`, `/api/dang-nhap`, `/api/dang-xuat`, `/api/toi`), Task 4 (`/api/chat`, `/api/chat/gui`).
- Hành vi: hai tab Đăng nhập / Đăng ký (kiểm nhập lại khớp ở trình duyệt trước khi gửi); sau đăng nhập: khung chat (khách phải, shop trái; tin `bot` có nhãn nhỏ "tự động", tin `he_thong` canh giữa), ô gửi (Enter gửi, tối đa 500 ký tự), "Shop đang soạn tin…" khi `dang_soan`, hỏi `/api/chat?sau=` mỗi 2 s, nút Đăng xuất, dòng nhắc demo. 429 → hiện "Gửi nhanh quá, thử lại sau N giây". Vai `shop` mở `khach.html` → link về `/`.

- [ ] **Step 1:** Viết hai file + CSS.
- [ ] **Step 2:** `node --check codebase/static/khach.js` → không lỗi.
- [ ] **Step 3:** Thử bằng Playwright (script trong scratchpad, máy chủ chạy `MODEL_PROVIDER` thật): đăng ký `demo1`, gửi "lấy 1 áo, Lan 0904444444, 12 Nguyễn Huệ, P. Bến Nghé, Q.1, TP.HCM" → thấy tin "Shop · tự động" chứa "đã ghi nhận đơn"; không có lỗi JS; chụp màn hình ở 390×844 và 1366×768.
- [ ] **Step 4:** Commit `static: trang khách đăng ký, đăng nhập, chat`.

### Task 6: Trang shop — đăng nhập, nhắn khách, tiếp quản

**Files:**
- Modify: `codebase/static/index.html`, `codebase/static/app.js`, `codebase/static/app.css`

**Interfaces:**
- Consumes: Task 3, Task 4 (`/api/shop/nhan`, `/api/shop/tra-bot`, `/api/shop/doc-lai`, khoá phiên `che_do`, `co_tin_chua_doc`, `tin`, `don_cu`).
- Hành vi: khởi động gọi `/api/toi`; không phải `shop` → form đăng nhập shop (không tải hộp thư); có nút Đăng xuất. Hội thoại `nguon == "khach"`: khung chat dựng từ `p.tin` (ghi rõ khách / bot tự động / shop / hệ thống); nhãn "Shop đang trả lời" (hộp thư + phiếu) khi `che_do == "shop"`; ô "Nhắn khách" (gửi → `/api/shop/nhan`), nút "Trả lại cho bot", nút "Cho AI đọc lại" khi `co_tin_chua_doc`; đơn cũ thu gọn phía trên phiếu; ẩn ô "Khách trả lời". Tự làm mới (cơ chế #59) bật khi có hội thoại `nguon == "khach"`, vẫn không vẽ lại phiếu đang mở nếu hội thoại đó không đổi (`trang_thai`, `phien_ban`, số tin). Mọi 401 → quay về form đăng nhập.

- [ ] **Step 1:** Sửa ba file.
- [ ] **Step 2:** `node --check codebase/static/app.js`.
- [ ] **Step 3:** Playwright hai ngữ cảnh: khách `demo2` gửi tin thiếu sđt → shop thấy cuộc chat lên đầu hộp thư trong ≤ 4 s; shop nhắn "Dạ cho em xin sđt ạ" → khách thấy tin "Shop" (không có nhãn "tự động"); khách gửi sđt → không có tin bot, shop thấy "Cho AI đọc lại"; shop "Trả lại cho bot", khách gửi tin → có tin bot; shop Duyệt → khách thấy "Đơn … đã được shop xác nhận". Không lỗi JS.
- [ ] **Step 4:** Commit `static: shop đăng nhập, nhắn khách, tiếp quản, đơn cũ`.

### Task 7: Deploy, tài liệu, chạy thật

**Files:**
- Modify: `deploy/nginx.conf`, `deploy/proxy.inc`, `compose.yaml`, `.env.example`, `.gitignore`, `spec.md` (§4 luồng E, §9, §10), `README.md`, `docs/deploy.md` (mục 4), `docs/huong-dan-demo.md`, `docs/ai-usage.md`

**Interfaces:**
- nginx: `limit_req_zone $khach zone=tk:10m rate=5r/m;` + `location ~ ^/api/(dang-ky|dang-nhap)$ { limit_req zone=tk burst=5 nodelay; … }`; regex zone `ai` (sau #61: `^/api/(moi|tra-loi|nhan-them)$`) thành `^/api/(moi|tra-loi|nhan-them|chat/gui)$`.
- `proxy.inc`: `proxy_set_header X-Real-IP $khach;` và `proxy_set_header X-Forwarded-Proto $j97_proto;` với `map $http_x_forwarded_proto $j97_proto { https https; default $scheme; }` trong `nginx.conf`.
- `compose.yaml` (service `be`): thêm `ADMIN_PASSWORD: ${ADMIN_PASSWORD:-admin}`, `TRUSTED_PROXY: 172.16.0.0/12` (`NAP_NEN`, `API_KEY_DEEPSEEK`, `FALLBACK_*` đã có từ #61).

- [ ] **Step 1:** Sửa cấu hình và tài liệu.
- [ ] **Step 2:** `docker compose config -q` → không lỗi; `docker compose up -d --build be` và `docker compose exec fe nginx -t && docker compose exec fe nginx -s reload`.
- [ ] **Step 3:** Kiểm trên https://j97.sunstack.org: `/api/hop-thu` chưa đăng nhập → 401; đăng ký 2 khách ở 2 trình duyệt, mỗi người chỉ thấy chat của mình; shop admin thấy cả hai; 6 tin / phút → 429.
- [ ] **Step 4:** `$PY run.py check` sạch; `$PY -m unittest discover -s tests` qua.
- [ ] **Step 5:** Commit `deploy, docs: chat khách HITL trên j97.sunstack.org`; push; mở PR vào `develop` (ghi rõ phụ thuộc #61).
