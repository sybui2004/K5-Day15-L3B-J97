# BE: màn hình duyệt (codebase/web.py) + agent. FE tĩnh do nginx phục vụ (deploy/nginx.conf), xem docs/deploy.md.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN useradd --system --uid 10001 --home-dir /app app \
    && mkdir -p data traces \
    && chown -R app:app data traces
USER app

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=600s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(urllib.request.urlopen('http://localhost:8000/api/hop-thu', timeout=4).status != 200)"

CMD ["python", "codebase/web.py"]
