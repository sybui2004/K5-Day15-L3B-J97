# Giữ Host gốc: web.py chỉ nhận Host có trong WEB_ALLOWED_HOSTS (chặn DNS rebinding).
proxy_set_header Host $http_host;   # giữ cả cổng (127.0.0.1:8080); $host sẽ bỏ cổng
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $http_x_forwarded_proto;
proxy_http_version 1.1;
proxy_set_header Connection "";
# Một lần chạy AI (guard + agent) có thể mất vài chục giây; web.py xử lý một yêu cầu một lúc.
proxy_connect_timeout 5s;
proxy_read_timeout 300s;
proxy_send_timeout 60s;
