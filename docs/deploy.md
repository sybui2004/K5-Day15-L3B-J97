# Triển khai bằng Docker Compose + Cloudflare Tunnel

Chạy màn hình duyệt J97 trên một máy Linux có Docker, đưa ra Internet ở `https://j97.sunstack.org` qua Cloudflare Tunnel. Máy không cần mở cổng vào, không cần IP công khai.

```
Khách ─HTTPS─▶ Cloudflare (sunstack.org) ─tunnel─▶ cloudflared ─▶ fe (nginx :80) ─/api/─▶ be (web.py :8000) ─▶ postgres
                                                                   └─ codebase/static/ (HTML, CSS, JS, fonts)
```

| Service | Image | Việc |
|---|---|---|
| `postgres` | `postgres:16-alpine` | Nhật ký duyệt + lần chạy AI (bảng `nhat_ky_duyet`, `lan_chay`, `kho.py` tự tạo). Volume `j97_pgdata`. Mạng `backend` là internal, không ra Internet |
| `be` | `local/j97-be` (build từ `Dockerfile`) | `codebase/web.py`: agent, guard, API `/api/*`. Không mở cổng ra máy |
| `fe` | `nginx:1.28.3-alpine` | Phục vụ `codebase/static/`, chuyển `/api/` sang `be`, giới hạn `/api/moi` 6 lần/phút/IP. Mở `127.0.0.1:8080` để kiểm tra trên máy |
| `cloudflared` | `cloudflare/cloudflared:2026.11.2` | Kết nối ra Cloudflare bằng token, chỉ chạy khi `.env` có `COMPOSE_PROFILES=tunnel` |

## 1. Chuẩn bị `.env`

```sh
cp .env.example .env        # nếu chưa có
openssl rand -hex 24        # dán vào POSTGRES_PASSWORD
```

Điền `MODEL_PROVIDER`, `MODEL_NAME`, `API_KEY` như khi chạy `python run.py`. `PUBLIC_HOST` là tên miền công khai (mặc định `j97.sunstack.org`). Lúc khởi động `be` chạy AI cho cả hộp thư mẫu, nên mỗi lần khởi động lại sẽ tốn một lượt gọi model.

## 2. Chạy và kiểm tra trên máy

```sh
docker compose up -d --build
docker compose ps                 # be healthy sau khi xử lý xong hộp thư
docker compose logs -f be
curl -s http://127.0.0.1:8080/api/hop-thu | head -c 200
```

## 3. Tạo tunnel trên Cloudflare dashboard

1. Vào [one.dash.cloudflare.com](https://one.dash.cloudflare.com) → **Networks → Tunnels → Create a tunnel** → chọn **Cloudflared** → đặt tên, vd `j97-mlops`.
2. Ở bước cài connector, chọn **Docker**. Chỉ copy phần token (chuỗi dài sau `--token`), dán vào `.env`:
   ```
   CLOUDFLARE_TUNNEL_TOKEN=eyJ...
   COMPOSE_PROFILES=tunnel
   ```
   Rồi chạy `docker compose up -d`. Dashboard báo connector **Healthy**.
3. Trong tunnel: **Routes → Add published application** (giao diện cũ: tab **Public Hostname**):
   - Subdomain `j97`, Domain chọn **`sunstack.org`** (ô này có thể mặc định là zone khác), Path để trống
   - Service URL **`http://fe:80`**: `http`, không phải `https`; `fe` là tên service nginx, không phải `localhost`

   Cloudflare tự tạo bản ghi DNS `j97.sunstack.org`. Nếu báo trùng thì xoá bản ghi `j97` cũ trong **DNS → Records** trước.
   Log `cloudflared` hiện `Updated to new configuration … "hostname":"j97.sunstack.org"` là tunnel đã nhận route.
4. Mở `https://j97.sunstack.org`.

Đổi tên miền khác thì sửa cả `PUBLIC_HOST` trong `.env` rồi `docker compose up -d be`, vì `web.py` từ chối Host lạ (403).

## 4. Cloudflare Access: công khai hay khoá

Tài khoản sunstack.org có app Access **sunstack-internal** phủ `*.sunstack.org` (policy `team-via-warp`): subdomain mới mặc định chỉ máy bật WARP của tổ chức mới vào được, máy khác nhận 403. Muốn đổi cho riêng `j97`, tạo app riêng; app có domain cụ thể được ưu tiên hơn wildcard.

**Access → Applications → Add an application → Self-hosted**, domain `j97.sunstack.org`, rồi chọn một policy:

- **Công khai (đang dùng):** Action **Bypass**, Include **Everyone**. Action **Allow** + Everyone vẫn bắt đăng nhập (302 sang trang login).
- **Chỉ người được mời:** Action **Allow**, Include **Emails** (email nhóm, giám khảo), bật Login method **One-time PIN**.

Khi công khai: màn hình duyệt không có đăng nhập, ai có link cũng duyệt / huỷ đơn được và gọi model bằng key của nhóm qua **Hội thoại mới**. nginx chỉ giới hạn `/api/moi` 6 lần/phút mỗi IP.

## Lỗi hay gặp

| Triệu chứng | Nguyên nhân |
|---|---|
| 403 trang "Cloudflare Access", không có form đăng nhập | App wildcard `*.sunstack.org` (team-via-warp) đang áp dụng: chưa có app riêng cho `j97` |
| 302 sang `…cloudflareaccess.com/…/login` | App riêng có policy Allow, chưa phải Bypass |
| 530, `error code: 1033` | DNS `j97` không trỏ vào tunnel đang chạy: tunnel chưa có route `j97.sunstack.org` |
| 502 | Service URL sai (`https://`, `localhost`) hoặc `fe` chưa chạy |
| 403 `{"loi": "Host không hợp lệ"}` | `PUBLIC_HOST` trong `.env` khác tên miền đang dùng |

## Vận hành

| Việc | Lệnh |
|---|---|
| Xem trạng thái | `docker compose ps` |
| Log | `docker compose logs -f be fe cloudflared` |
| Cập nhật code | `git pull && docker compose up -d --build` (sửa riêng `codebase/static/` thì chỉ cần tải lại trang) |
| Dừng / chạy lại | `docker compose stop` · `docker compose up -d` |
| Xem nhật ký trong DB | `docker compose exec postgres psql -U j97 -d j97 -c 'select * from nhat_ky_duyet order by id desc limit 10'` |
| Sao lưu DB | `docker compose exec -T postgres pg_dump -U j97 j97 > j97-$(date +%F).sql` |
| Xoá sạch kể cả dữ liệu | `docker compose down -v` |

Xoay token tunnel: dashboard → tunnel → **Refresh token**, dán token mới vào `.env`, `docker compose up -d cloudflared`.
