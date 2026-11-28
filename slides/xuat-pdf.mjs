// Xuất slides/demo-slides.html thành demo-slides.pdf ở gốc repo.
// Cài một lần:  (cd slides && npm i --no-save playwright@1.65.1 && npx playwright install chromium)
// Chạy:        node slides/xuat-pdf.mjs   (đứng ở đâu cũng được, đường dẫn tính từ vị trí file này)
import { chromium } from "playwright";
import { fileURLToPath } from "node:url";

const goc = new URL("..", import.meta.url);
const vao = new URL("slides/demo-slides.html", goc).href;
const ra = fileURLToPath(new URL("demo-slides.pdf", goc));

const trinhDuyet = await chromium.launch();
const trang = await trinhDuyet.newPage();
await trang.goto(vao, { waitUntil: "load" });
await trang.pdf({ path: ra, preferCSSPageSize: true, printBackground: true });
await trinhDuyet.close();
console.log("Đã ghi " + ra);
