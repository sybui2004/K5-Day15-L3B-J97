# Tài khoản khách, đăng nhập shop và chat HITL — thiết kế

Ngày 28/11/2026 · người quyết: Sỹ (đội trưởng) · trạng thái: chờ duyệt

## 1. Vì sao làm

Buổi demo chạy trên bản deploy công khai https://j97.sunstack.org (PR #61: Docker Compose, nginx, Cloudflare Tunnel). Sỹ muốn **người xem tự đóng vai khách**: mở trang trên máy của họ, đăng ký, nhắn chốt đơn; **Sỹ đóng vai shop** trên màn hình duyệt. Bot (luồng AI hiện có) tự trả lời khách và lên đơn nháp, nhưng shop phải **nhắn được cho khách bất cứ lúc nào** (human-in-the-loop): đây là điểm Sỹ muốn cho giám khảo thấy.

Lý do thứ hai: bản deploy đang không có đăng nhập. Ai có link cũng xem được Hộp thư, Nhật ký (trace có tên, sđt, địa chỉ), bấm Duyệt / Huỷ và tốn tiền gọi model (reviewer PR #61, P1). Đăng nhập shop vá lỗ hổng này ở tầng ứng dụng.

## 2. Mục tiêu, không làm, không được xảy ra

**Mục tiêu**
- Khách: đăng ký (username, mật khẩu, nhập lại mật khẩu), đăng nhập (username, mật khẩu), một khung chat với shop, thấy tin trả lời của bot và của shop.
- Shop: đăng nhập `admin` / mật khẩu (mặc định `admin`), thấy mọi cuộc chat của khách trong Hộp thư, duyệt đơn như bây giờ, nhắn cho khách, tiếp quản và trả lại cho bot.
- Chặn spam đăng ký và chặn gửi tin dồn dập (mỗi tin khách tốn một lượt gọi model).

**Không làm (lần này)**
- Kênh chat thật (Messenger, Zalo, Telegram), WebSocket / đẩy tin tức thì: dùng hỏi tin mới định kỳ.
- Quên mật khẩu, đổi mật khẩu, email, nhiều tài khoản shop, phân quyền chi tiết.
- Chạy AI song song: AI vẫn chạy lần lượt (xem §4).
- Sửa luồng AI, prompt, lớp chặn NeMo, dự phòng DeepSeek, công cụ, bộ câu thử, metric, chuẩn "đạt".

**Không được xảy ra (dù chạy được vẫn là thất bại)**
- Khách đọc được hội thoại, đơn, trace, nhật ký của người khác, hoặc gọi được API của shop.
- Bot báo khách "đã lên đơn" trước khi shop duyệt.
- Shop đã tiếp quản mà bot vẫn chen vào trả lời.
- Một người spam đăng ký / gửi tin làm cạn credit model hoặc làm treo trang cho người khác.

## 3. Ràng buộc

- Python thư viện chuẩn, không thêm gói (requirements chỉ có `anthropic`, `nemoguardrails`, `psycopg` tuỳ chọn). Mật khẩu băm bằng `hashlib.scrypt` (hoặc `pbkdf2_hmac`) + muối ngẫu nhiên, so bằng `hmac.compare_digest`.
- Máy chủ là `http.server` trong `codebase/web.py`. Đổi sang `ThreadingHTTPServer` (`daemon_threads = True`) để nhiều khách hỏi tin cùng lúc không phải xếp hàng sau một lần gọi AI.
- `tracing` giữ lần chạy hiện tại trong biến toàn cục: mọi lần chạy AI đi qua `_khoa_ai` (có từ #59), lần lượt. Thứ tự khoá `_khoa` rồi `_khoa_ai`; luồng nền không giữ `_khoa` khi chờ AI.
- Trên deploy, nginx trả thẳng file trong `codebase/static/` (không qua web.py) và chỉ proxy `/api/*`. Vì vậy **mọi kiểm tra đăng nhập và phân vai nằm ở web.py**; HTML/JS tải được tự do, dữ liệu thì không.
- CSP của nginx: `script-src 'self'`, `style-src 'self'`, `form-action 'none'` → không script / style nội dòng, form gửi bằng `fetch` (như hiện tại).
- Chống CSRF giữ cơ chế hiện có: POST phải có header `X-Man-Hinh-Duyet: 1` và `Content-Type: application/json` (`post_hop_le`); thêm cookie `SameSite=Strict`.
- Host: giữ `host_hop_le` + `WEB_ALLOWED_HOSTS` của PR #61.
- Lưu trữ: deploy chạy `DATABASE_REQUIRED=1` (Postgres bắt buộc; file trong container mất khi tạo lại). Chạy máy bằng `python run.py` không có Postgres thì ghi file trong `data/` (gitignore), như `KhoFile`.
- Hạn: CP4 14:30 28/11 đã qua khi làm; mọi thay đổi ghi `spec.md` §10, không sửa câu thử, §7, metric, kết quả các lượt đã chạy.

## 4. Các cách đã cân nhắc

| Cách | Được | Mất | Chọn? |
|---|---|---|---|
| **1. Mở rộng web.py hiện tại**: ThreadingHTTPServer, trang `/khach`, cookie phiên, Postgres qua `kho.py`, hỏi tin mới mỗi 2 s, tin khách vào hàng đợi xử lý ở luồng nền như #59 | Không thêm thư viện; dùng lại luồng AI, NeMo, dự phòng, phiếu duyệt, `phien_ban`; chạy ngay trên stack deploy | Chậm hơn chat thật ≤ 2 s; AI lần lượt nên 20 người nhắn cùng lúc thì người cuối chờ cỡ 1 phút (hiện "Shop đang soạn tin…") | **Chọn** (Sỹ chọn) |
| 2. Viết lại FastAPI + WebSocket | Thời gian thực, chịu tải tốt | Viết lại gần hết web.py, thêm thư viện, Dockerfile, test | Không |
| 3. Nối Telegram / Messenger | Khách dùng app quen | Cần bot / webhook, người xem phải có app, không có form đăng ký Sỹ muốn | Không |

Bước sau nếu tải nặng: cho `tracing` một trace riêng mỗi luồng để AI chạy song song; không đổi kiến trúc.

## 5. Phần đã quyết

### 5.1 Vai, tài khoản, mật khẩu
- Hai vai: `khach`, `shop`. Tài khoản shop duy nhất: username `admin`, mật khẩu đọc từ `ADMIN_PASSWORD` (`.env`, compose truyền vào service `be`); không đặt thì là `admin` (đúng yêu cầu demo), máy chủ in cảnh báo khi đang dùng mật khẩu mặc định trên Host công khai. Tài khoản shop không tạo qua form đăng ký; username `admin` bị cấm khi đăng ký.
- Đăng ký: username 3–32 ký tự `[a-z0-9_.]`, chuyển chữ thường, duy nhất; mật khẩu 6–128 ký tự, "nhập lại" phải khớp (kiểm ở cả giao diện và máy chủ). Không thu email, sđt, tên thật.
- Đăng ký thành công thì đăng nhập luôn.

### 5.2 Phiên đăng nhập
- Token ngẫu nhiên 32 byte (`secrets.token_urlsafe`); lưu **băm SHA-256** của token, tài khoản, vai, hạn (12 giờ). Cookie `j97_phien`: `HttpOnly`, `SameSite=Strict`, `Path=/`, `Secure` khi `X-Forwarded-Proto: https` (Cloudflare → nginx → be). Có `POST /api/dang-xuat` xoá phiên.
- `GET /api/toi` → `{vai, username}` hoặc 401: giao diện dùng để chọn màn hình.

### 5.3 Chặn spam
- Người xem vào chủ yếu bằng **4G** (Sỹ xác nhận), nên giới hạn theo IP dùng được; vẫn để mức rộng một chút vì 4G có thể dùng chung IP (CGNAT).
- Trong web.py (để chạy máy không có nginx vẫn có): đăng ký ≤ 5 tài khoản / IP / giờ; đăng nhập sai ≤ 10 lần / 10 phút / (IP, username); khách gửi tin ≤ 5 tin / phút / tài khoản, tin ≤ 500 ký tự, ≤ 200 tin / tài khoản; **trần chung** ≤ 60 tin khách / phút cho cả máy chủ (giữ credit model). Vượt thì 429 + "thử lại sau N giây".
- IP thật *(quyết định của người viết)*: `deploy/proxy.inc` (PR #61) đang đặt `X-Real-IP $remote_addr` (là IP của cloudflared) và chuyển nguyên `X-Forwarded-Proto` của người gọi. Sửa: nginx **ghi đè** `X-Real-IP` bằng `$khach` (`CF-Connecting-IP`, rỗng thì địa chỉ kết nối) và tự đặt `X-Forwarded-Proto` (https khi có `CF-Visitor`/`X-Forwarded-Proto` từ cloudflared, ngược lại `$scheme`); web.py **chỉ tin** hai header này khi kết nối đến từ mạng nội bộ compose (đặt bằng biến `TRUSTED_PROXY`, vd `172.16.0.0/12`); chạy máy thì dùng địa chỉ kết nối và không đặt `Secure`. Phối hợp với phiên lo PR #61 vì `proxy.inc` thuộc PR đó.
- nginx (`deploy/nginx.conf` của PR #61, bản cuối ở commit `8ab811c`): thêm `limit_req_zone` riêng cho `/api/dang-ky` và `/api/dang-nhap` (vd 5 lần / phút / IP, dùng `map $khach` sẵn có); đưa `/api/chat/gui` vào chung zone `ai` (6 / phút / IP) bằng cách mở rộng regex `location ~ ^/api/(moi|tra-loi)$` thành `^/api/(moi|tra-loi|chat/gui)$` (`/api/shop/nhan` không gọi model nên để ở zone `api`).

### 5.4 Cuộc chat của khách
- Mỗi tài khoản khách là **một cuộc chat** với shop, là một hội thoại trong Hộp thư của shop: mã `TK-<username>`, `ma_khach` = `TK-<username>`, `nguon` = `khach`. Lịch sử khách cũ (`get_customer_history`) không dùng cho tài khoản mới (không có trong `lich-su-khach.csv`).
- **Nhiều đơn trong một cuộc chat** (Sỹ đồng ý): sau khi đơn được Duyệt hoặc Huỷ, khách nhắn tiếp thì **bắt đầu đơn mới trong cùng cuộc chat**. Mỗi lần Duyệt / Huỷ đặt một **mốc**; AI chỉ đọc các tin **sau mốc gần nhất**, nên đơn cũ không lẫn vào đơn mới. Cuộc chat quay lại trạng thái xử lý như hội thoại mới (`phien_ban` tăng, `ma_don` của đơn mới). Đơn cũ vẫn xem được: mỗi mốc lưu mã đơn, kết quả (đã duyệt / đã huỷ), trường đã duyệt. Giao diện shop hiện đơn cũ thu gọn phía trên đơn đang xử lý; khung chat vẫn hiện toàn bộ tin.
- Tin nhắn có 4 loại người nói: `khach`, `bot`, `shop`, `he_thong`. Văn bản đưa cho AI ghép như hộp thư hiện có: `Mã khách: TK-… | Khách: … | Shop: …` (tin `bot` và `shop` đều là "Shop:"; tin `he_thong` không đưa vào).
- **Chế độ bot** (mặc định): mỗi tin khách mới → cuộc chat vào hàng đợi → luồng nền chạy `xu_ly` trên toàn bộ văn bản (như `them_tra_loi`), cập nhật `kq`, `trang_thai`, `trace`, tăng `phien_ban` → thêm tin `bot`:
  - HỎI LẠI / TỪ CHỐI: nội dung `tin_gui_khach` của AI.
  - TẠO ĐƠN NHÁP: "Dạ shop đã ghi nhận đơn của anh/chị: <người nhận · sđt · địa chỉ · sản phẩm × số lượng>. Shop kiểm lại rồi xác nhận ngay ạ." — **không** dùng câu "shop đã lên đơn".
  - Khách gửi thêm tin khi lần chạy trước còn trong hàng đợi: gộp, chỉ chạy một lần trên văn bản mới nhất.
  - Đang chờ AI: khách thấy "Shop đang soạn tin…".
- **Shop tiếp quản** (cách A Sỹ chọn): shop gửi tin trong một cuộc chat → cuộc chat sang chế độ `shop`, bot dừng ở cuộc chat đó; tin khách sau đó chỉ được lưu, không chạy AI. Nhãn "Shop đang trả lời" trên Hộp thư và trên phiếu. Nút **"Trả lại cho bot"** → chế độ `bot`; bot chạy lại từ tin khách **tiếp theo** (không tự chạy ngay).
- *(Quyết định của người viết)* Shop tiếp quản đúng lúc AI đang chạy dở: kết quả AI **vẫn cập nhật** `kq`, `trang_thai`, `phien_ban` (đơn nháp mới nhất) nhưng **không thêm tin `bot`**. Ở chế độ `shop`, mỗi tin khách mới **tăng `phien_ban`** và gắn cờ "có tin mới AI chưa đọc" → phiếu đang mở thành cũ (cơ chế #56), shop không duyệt được theo phiếu lỗi thời. Nút **"Cho AI đọc lại"** chạy `xu_ly` trên tin sau mốc để cập nhật đơn nháp, không nhắn gì cho khách.
- **Duyệt / huỷ**: shop bấm Duyệt → thêm tin `he_thong` cho khách: "Đơn <mã đơn> đã được shop xác nhận." Huỷ đơn nháp → không tự nhắn (shop tự nhắn nếu muốn). Chống duyệt phiếu cũ (`phien_ban`, #56) giữ nguyên: tin khách mới làm AI đọc lại → phiên bản tăng.
- Khách chỉ thấy tin của cuộc chat mình: `khach`, `bot`, `shop`, `he_thong` (không thấy trace, `kq`, nhật ký). Tin bot và tin shop đều hiện là "Shop", có nhãn nhỏ "tự động" cho tin bot (để người xem thấy được HITL).

### 5.5 API

Khách / chung (không cần đăng nhập, trừ khi ghi rõ):
- `POST /api/dang-ky {username, mat_khau, nhap_lai}` · `POST /api/dang-nhap {username, mat_khau}` · `POST /api/dang-xuat` · `GET /api/toi`.
- (khách) `GET /api/chat?sau=<id>` → tin mới hơn `id` + `{dang_soan: bool}` · `POST /api/chat/gui {tin}`.

Shop (mọi endpoint hiện có, thêm vào): `GET /api/hop-thu`, `GET /api/nhat-ky`, `POST /api/kiem|duyet|huy|tra-loi|moi|nhan-them` **đều yêu cầu vai `shop`** (401 chưa đăng nhập, 403 sai vai). Thêm `POST /api/shop/nhan {ma, tin}` (gửi tin cho khách, bật tiếp quản), `POST /api/shop/tra-bot {ma}`.

### 5.6 Giao diện
- `codebase/static/khach.html` (+ `khach.js`, dùng chung `app.css`): đăng nhập / đăng ký (hai tab), khung chat, ô gửi, "Shop đang soạn tin…", nút đăng xuất. Dòng nhắc cố định: "Bản demo — đừng nhập tên, số điện thoại, địa chỉ thật."
- Trang shop `index.html`: gọi `/api/toi`; chưa đăng nhập hoặc không phải shop → hiện form đăng nhập shop (không chuyển trang khác). Có nút đăng xuất.
- Hộp thư shop: cuộc chat của khách lên đầu khi có tin mới; nhãn "Shop đang trả lời" khi tiếp quản. Khung giữa: chat hiện rõ ai nói (khách / bot tự động / shop / hệ thống). Thêm ô **"Nhắn khách"** và nút **"Trả lại cho bot"** cho hội thoại `nguon = khach`. Ô "Khách trả lời" (shop dán tin khách) chỉ còn cho hội thoại mẫu / gõ tay.
- Hỏi tin mới: trang khách 2 s; trang shop dùng cơ chế tự làm mới của #59, bật luôn khi có cuộc chat khách (không chỉ khi `dang_xu_ly`), vẫn không vẽ lại phiếu đang mở nếu hội thoại đó không đổi.
- `/` trên deploy vẫn là trang shop; trang khách ở `/khach.html` (link đưa người xem, kèm mã QR trên slide nếu kịp).

### 5.7 Lưu trữ
- Bảng mới (Postgres, tạo cùng `BANG` trong `kho.py`): `tai_khoan(id, username unique, mat_khau_bam, vai, tao_luc, ip_tao)`, `phien_dang_nhap(token_bam pk, tai_khoan_id, het_han)`, `tin_nhan(id serial, tai_khoan_id, nguoi_noi, noi_dung, luc)`, `cuoc_chat`, `don_cu` (cột ở dưới).
- `KhoFile` (chạy máy): file JSON / JSONL tương ứng trong `data/` (gitignore).
- *(Quyết định của người viết)* Trạng thái cuộc chat **được lưu** để khởi động lại không mất: `cuoc_chat(tai_khoan_id pk, che_do, trang_thai, phien_ban, kq jsonb, ma_don, ma_van_don, co_tin_chua_doc, moc_tin_id)` và `don_cu(id, tai_khoan_id, moc_tin_id, ket_qua, ma_don, truong jsonb, luc)`. Trace (`trace`) không lưu vào `cuoc_chat` (đã có ở `lan_chay`). Máy chủ khởi động lại: dựng lại cuộc chat từ hai bảng này, không gọi lại AI.
- Lần chạy AI của cuộc chat khách ghi `lan_chay` như hiện có (trace có dữ liệu khách → §9).

### 5.8 Tài liệu phải sửa cùng
- `spec.md` §4 (thêm luồng E: khách tự nhắn, shop tiếp quản), §9 (dữ liệu người xem nhập trên bản deploy công khai, lưu ở đâu, xoá sau demo; "gửi tin cho khách" nay có trong trang demo), §10 changelog.
- README bảng "Phần nào thật, phần nào giả" (dòng "Gửi tin cho khách"), `.env.example` (`ADMIN_PASSWORD`), `docs/deploy.md` mục 4 (Cloudflare Access: trang công khai nhưng API có đăng nhập), `docs/huong-dan-demo.md` (kịch bản người xem làm khách), `docs/ai-usage.md`.

### 5.9 Kiểm thử
- unittest: băm / kiểm mật khẩu; đăng ký (trùng, `admin`, nhập lại sai, giới hạn IP); đăng nhập sai bị chặn; phiên hết hạn; cookie có `Secure` khi `X-Forwarded-Proto: https`; mọi API shop trả 401/403 với khách và với người chưa đăng nhập; khách chỉ đọc được tin của mình; chế độ bot → có tin `bot`; TẠO ĐƠN NHÁP → câu "đã ghi nhận", không có "đã lên đơn"; tiếp quản → tin khách không chạy AI; trả lại bot → tin kế tiếp chạy AI; duyệt → tin `he_thong`; gộp tin trong hàng đợi; dựng lại sau khởi động.
- Chạy thật trên deploy: 2 tài khoản khách ở 2 trình duyệt + shop; người này không thấy tin người kia; đếm thời gian chờ khi 5 khách gửi cùng lúc.

## 6. Nhánh và thứ tự làm

*(Quyết định của người viết)* PR #61 (deploy) chưa vào `develop` và tách từ trước #59, #60; nhánh này (`feature/chat-khach-hitl`) tách từ `develop` sau #60. Làm: merge `origin/feature/deploy-docker-cloudflare` (commit `8ab811c`) vào nhánh này trước khi viết code, để có `WEB_ALLOWED_HOSTS`, `DATABASE_REQUIRED`, `deploy/`, `compose.yaml`; thêm `ADMIN_PASSWORD`, `TRUSTED_PROXY` vào `compose.yaml` (service `be`) và `.env.example`. PR vào `develop` sau khi #61 merge (khi đó diff chỉ còn phần tính năng này).

## 7. Để người làm tự quyết
Bố cục, câu chữ giao diện ngoài các câu đã ghi; định dạng file của `KhoFile`; khoảng hỏi tin (≈ 2 s); cách hiện "Shop đang soạn tin…"; chia nhỏ commit / PR; có dọn phiên hết hạn định kỳ hay không.
