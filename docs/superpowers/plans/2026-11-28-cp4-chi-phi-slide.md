# CP4 · chi phí + bản nháp slide — kế hoạch làm

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Điền chi phí khi dùng thật (guide 4.2) từ một lượt `simulate` trên `develop` đã có #46, rồi dựng bản nháp slide 8 trang xuất `demo-slides.pdf`.

**Architecture:** `cost/personas.yaml` → `python run.py simulate --rate-from eval/run-5.csv` sinh `cost/simulate-1*` → chép số sang `cost/cost-estimate.md`, `spec.md` §8 → slide HTML một file `slides/demo-slides.html` lấy số từ các file đó → `slides/xuat-pdf.mjs` (Playwright, Chromium headless) in ra `demo-slides.pdf`.

**Tech Stack:** Python 3 (`.venv` của repo chính, có `anthropic`), Node 18+ / `npx`, Playwright 1.49.1.

**Spec:** `docs/superpowers/specs/2026-11-28-cp4-chi-phi-slide-design.md`

## Global Constraints

- Worktree `/project/template-devops/K5-Day15-L3B-J97-cp4-chi-phi`, nhánh `feature/cp4-chi-phi`, PR vào `develop` (`gh … --repo sybui2004/K5-Day15-L3B-J97`), người duyệt Hưng (§8 là phần của Hưng).
- Python: `PY=/project/template-devops/K5-Day15-L3B-J97/.venv/bin/python`. Venv này chỉ cấp thư viện (`anthropic`). Cấu hình model do `codebase/ai.py` đọc từ `.env` **ở gốc worktree này**, thiếu thì lặng lẽ chạy `fake` → xem Task 1 Step 2.
- `SCRATCH` = thư mục tạm của phiên làm việc (ngoài repo): ảnh kiểm PDF và PyMuPDF để ở đây, không commit.
- Không sửa `cost/simulate.py`, `run.py`, `eval/`, `codebase/`. Không sửa `cost/simulate-1.*` sau khi chạy; chạy lại thì thành `simulate-2`.
- Không commit `.env`. Commit message và mô tả PR không có `Co-Authored-By` hay dòng "Generated with".
- Số không có nguồn ghi *(tự ước tính)*. Lượt 2 = `run-5@20261128-021955`, 28/30 (93%), đạt chuẩn — chép, không tính lại.
- Giá (USD / 1M token, vào / ra): Haiku 5.5 0.10 / 0.50 · Sonnet 5.5 2.00 / 10.00 · Opus 5.5 4.00 / 20.00, nguồn `further-reading/model-prices.md` (BTC xem 25/11/2026).
- Người dùng = 11.606 (Thanh Niên 04/12/2024, link trong spec) × hệ số phủ × tỉ lệ thuộc lát cắt × tỉ lệ sử dụng → low 580 · base 1741 · high 5803. Ba thừa số sau đều *(tự ước tính)*, nhóm chốt trước Task 1 Step 3 (bảng ở spec, mục "Đầu vào đã chốt").

## Review Focus

1. Số lệch giữa `simulate-1-summary.md`, `cost-estimate.md`, `spec.md` §8 và slide → Task 3 có bước so tự động.
2. Chữ tiếng Việt có dấu mất dấu / ra ô vuông trong PDF (thiếu font ở Chromium headless) → Task 3 chụp trang PDF ra ảnh và xem.
3. Chữ tràn khỏi trang 16:9, một `<section>` thành 2 trang PDF → Task 3 kiểm PDF đúng 8 trang.
4. `simulate` in cảnh báo nguồn trống / "(ví dụ)" → Task 1 kiểm log không có dòng cảnh báo.
5. Lượt nộp chạy nhầm model `fake` (worktree thiếu `.env`) → Task 1 Step 2 kiểm tên model và token trong trace trước lượt nộp.
6. PDF ghi nhầm vào `slides/` thay vì gốc repo → `xuat-pdf.mjs` tính đường dẫn từ vị trí script; Task 3 kiểm file ở gốc.
7. Lỡ commit `.env` hoặc `slides/node_modules` → mỗi task kiểm `git status` trước commit.

---

### Task 1: personas.yaml có nguồn + lượt mô phỏng nộp

**Files:**
- Modify: `cost/personas.yaml` (bản nháp đã có trong worktree, chưa commit)
- Create (sinh ra): `cost/simulate-1.csv`, `cost/simulate-1-summary.md`, `traces/simulate-1.jsonl`
- Add: `docs/superpowers/specs/2026-11-28-cp4-chi-phi-slide-design.md`, file plan này

**Interfaces:**
- Produces: `cost/simulate-1-summary.md` — bảng persona + bảng chi phí 3 model; các task sau chép số từ đây.

- [ ] **Step 1:** Đối chiếu `cost/personas.yaml` với spec mục "Đầu vào đã chốt" (3 persona, share, uses, turns, 3 giá, nguồn). Bản nháp đang ghi `users` 1161 / 11606 / 23212: đổi sang 580 / 1741 / 5803 (hoặc số nhóm chốt), và `users.source` ghi đủ bốn thừa số, đánh dấu ba tỉ lệ là *(tự ước tính)* cho cả kịch bản cơ sở. Dòng 6 khung đã đổi để không còn chuỗi "(ví dụ)".
- [ ] **Step 2:** Cấp cấu hình model cho worktree rồi chạy thử.
  - Worktree cần `.env` riêng ở gốc (đã gitignore). Nếu chưa có: `cp /project/template-devops/K5-Day15-L3B-J97/.env .env`. Kiểm mà không in khoá: `grep -E '^(MODEL_PROVIDER|MODEL_NAME)=' .env` và `grep -c '^API_KEY=.\+' .env` → `1`.
  - Chạy thử: `$PY run.py simulate --try 3 --rate-from eval/run-5.csv`. Mong đợi: 0 phiên lỗi, "Tỉ lệ đạt dùng để tính: 28/30 (93%) — lượt run-5@20261128-021955", không có dòng ⚠️ về nguồn / ví dụ.
  - Kiểm model thật: `$PY -c "import json;e=[json.loads(l) for l in open('traces/simulate-try.jsonl')];m=[x for x in e if x.get('kind')=='model'];print({x.get('model') for x in m}, sum(x.get('tokens_in') or 0 for x in m), sum(x.get('tokens_out') or 0 for x in m))"` → tập model chỉ gồm `claude-sonnet-5-5…`, hai tổng token > 0. Ra `fake` hoặc token 0 thì dừng, sửa `.env`, không chạy Step 3.
  - Xoá `cost/simulate-try*`, `traces/simulate-try.jsonl`.
- [ ] **Step 3:** Nhóm đã chốt ba thừa số *(tự ước tính)* của số người dùng (hoặc đồng ý mặc định trong spec). Chạy nộp: `$PY run.py simulate --rate-from eval/run-5.csv` (50 phiên, ≈ $0.5). Mong đợi: "Phiên lỗi … 0/50", ghi `cost/simulate-1.*`.
- [ ] **Step 4:** `git status --short` chỉ có `cost/personas.yaml`, `cost/simulate-1.csv`, `cost/simulate-1-summary.md`, `traces/simulate-1.jsonl`, `docs/superpowers/…`. Commit:

```bash
git add cost/personas.yaml cost/simulate-1.csv cost/simulate-1-summary.md traces/simulate-1.jsonl docs/superpowers
git commit -m "cost: persona từ phỏng vấn P1–P4, quy mô Cục Thuế TP.HCM, giá 3 model; simulate-1 (50 phiên, tỉ lệ đạt run-5)"
```

### Task 2: cost-estimate.md + spec §8, §10

**Files:**
- Modify: `cost/cost-estimate.md` (§1–§4), `spec.md` §8, bảng §10 "CP2 → CP4"

**Interfaces:**
- Consumes: `cost/simulate-1-summary.md` (Task 1).
- Produces: `cost/cost-estimate.md` §2 bảng 3 model, §3 dòng "Kết luận một dòng" — slide trang 6, 7 chép nguyên.

- [ ] **Step 1:** §1 Đầu vào: điền persona + nguồn, bảng số người dùng (quy mô tham chiếu × ba thừa số, như spec), 3 giá + link + ngày, tỉ lệ đạt 28/30 (93%) `run-5`, "đo token trên claude-sonnet-5-5, tính giá Haiku 5.5 và Opus 5.5".
- [ ] **Step 2:** §2 dán nguyên bảng chi phí từ summary (giữ đủ cột của khung), ghi `cost/simulate-1.csv` · 50 phiên · seed 42. Ngay dưới bảng ghi hai giả định của dòng Haiku / Opus: token đo trên Sonnet 5.5, và "chi phí / task thành công" dùng tỉ lệ đạt 28/30 của Sonnet.
- [ ] **Step 3:** §3 theo mục "Cách kết luận" của spec:
  - Phần **đang mất** / shop / tháng: 195.000–494.000đ ÷ 4 ≈ 49.000–124.000đ phí ship (§2, đầu trên *(tự ước tính)*) và 855 phút ÷ 4 ≈ 214 phút. Ghi rõ chưa đo AI tránh được bao nhiêu phần.
  - Chi phí / shop / tháng (cơ sở) C theo từng model, đổi ra VND bằng một tỷ giá có link + ngày xem (Vietcombank, bán ra).
  - Bảng ngưỡng hoà vốn f\* = C ÷ phí ship đang mất, ở đầu dưới và đầu trên, cho từng model; f\* > 100% ghi "phí ship không đủ bù".
  - Kết luận một dòng có điều kiện, nêu f\* và ba thứ nó phụ thuộc (C, tỉ lệ lỗi tránh được, tỉ lệ đạt eval của model rẻ). Không viết "đáng làm" khi chưa có hai số sau.
- [ ] **Step 4:** §4 ngắn: độ nhạy đổi model (Haiku / Sonnet / Opus từ bảng), chi phí ngoài model (giờ người duyệt — ghi chưa tính).
- [ ] **Step 5:** `spec.md` §8 bốn dòng theo khung (file persona, `simulate-1` 50 phiên, chi phí / task thành công 2 model kèm hai giả định, chi phí / tháng thấp · cơ sở · cao kèm "số người dùng dựa trên tỉ lệ tự ước tính", đáng làm không = câu có điều kiện theo f\*). §10 thêm một dòng (giờ · đổi gì · vì sao: guide 4.2, không đổi câu thử, §7, metric).
- [ ] **Step 6:** Kiểm: `grep -n "__" cost/cost-estimate.md` không còn ô trống trong §1–§3; `$PY run.py check` sạch; mỗi số tiền trong §2 có trong `cost/simulate-1-summary.md` (`grep -F`); tính tay lại f\* từ C và hai đầu phí ship. Commit `cost, spec §8: chi phí khi dùng thật từ simulate-1`.

### Task 3: bản nháp slide + demo-slides.pdf

**Files:**
- Create: `slides/demo-slides.html`, `slides/xuat-pdf.mjs`, `demo-slides.pdf`
- Modify: `slides/outline.md` (cột Xong), `.gitignore` (thêm `slides/node_modules/`)

**Interfaces:**
- Consumes: `evidence/summary.md`, `spec.md` §2 §4, `eval/report.md`, `eval/README.md`, `eval/run-5.csv`, `cost/cost-estimate.md` (Task 2).
- Produces: `node slides/xuat-pdf.mjs` → `demo-slides.pdf` ở gốc repo.

- [ ] **Step 1:** `slides/demo-slides.html`: một file tự chứa, 8 `<section class="slide">` theo bảng `slides/outline.md`, `@page { size: 13.333in 7.5in; margin: 0 }`, mỗi section đúng một trang (`break-after: page`, `overflow: hidden`). Font: hệ thống có dấu tiếng Việt (vd `"Noto Sans", "DejaVu Sans", sans-serif`). Mỗi trang ghi nguồn số ở chân trang (tên file). Trang 4: một câu `thuong` và một câu `kho` quy đổi địa chỉ cũ, input + output thật từ `eval/run-5.csv`. Trang 7: bảng ngưỡng hoà vốn f\* theo model (chép từ `cost-estimate.md` §3), hai giả định của dòng Haiku / Opus, số người dùng ghi "dựa trên tỉ lệ tự ước tính", đề xuất có điều kiện, ghi "nhóm chốt".
- [ ] **Step 2:** `slides/xuat-pdf.mjs`: Playwright chromium. Mọi đường dẫn tính từ vị trí script, không phụ thuộc thư mục đang đứng: `const goc = new URL("..", import.meta.url)`, mở `new URL("slides/demo-slides.html", goc).href`, `page.pdf({ path: fileURLToPath(new URL("demo-slides.pdf", goc)), preferCSSPageSize: true, printBackground: true })`, in ra đường dẫn đã ghi.
  - Cài một lần: `(cd slides && npm i --no-save playwright@1.49.1 && npx playwright install chromium)`.
  - Xuất, **chạy từ gốc repo**: `node slides/xuat-pdf.mjs`. Kiểm: `ls -l demo-slides.pdf` có ở gốc và `test ! -e slides/demo-slides.pdf`.
- [ ] **Step 3:** Kiểm PDF đúng 8 trang: `$PY -c "import re;print(len(re.findall(rb'/Type\s*/Page[^s]', open('demo-slides.pdf','rb').read())))"` → `8`.
- [ ] **Step 4:** Render **chính file `demo-slides.pdf`** ra ảnh (không chụp HTML), để thấy lỗi font, cắt chữ và ngắt trang như khi in. Máy không có `pdftoppm`, nên cài PyMuPDF vào scratchpad, không vào `.venv` hay repo:
  - `$PY -m pip install --target "$SCRATCH/pymupdf" pymupdf`
  - `PYTHONPATH="$SCRATCH/pymupdf" $PY -c "import fitz,sys;d=fitz.open('demo-slides.pdf');[p.get_pixmap(dpi=80).save(f'{sys.argv[1]}/trang-{i+1}.png') for i,p in enumerate(d)]" "$SCRATCH"`
  - Xem cả 8 ảnh: không mất dấu / ô vuông, không chữ bị cắt ở mép, mỗi slide đúng một trang.
- [ ] **Step 5:** So số: mọi số tiền và tỉ lệ trên trang 5–7 có trong `eval/report.md` hoặc `cost/cost-estimate.md` (`grep -F`).
- [ ] **Step 6:** `slides/outline.md` tích Xong các trang đã có; bảng "Ai nói trang nào" để trống. `git status` không có `node_modules`, `.env`. Commit `slides: bản nháp 8 trang + demo-slides.pdf, lệnh xuất PDF`.

### Task 4: PR

- [ ] **Step 1:** `git fetch && git rebase origin/develop`, `$PY -m unittest discover -s tests` và `$PY run.py check` sạch.
- [ ] **Step 2:** Push, mở PR vào `develop` (`--repo sybui2004/K5-Day15-L3B-J97`), mô tả: đã làm gì, số chính (chi phí / task thành công 2 model, chi phí / shop / tháng), chỗ tự ước tính, phần chưa làm (go/iterate/stop nhóm chốt, bảng người nói, video), nhờ Hưng duyệt. Không có dòng "Generated with".
