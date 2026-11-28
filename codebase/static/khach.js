"use strict";
// Trang khách: đăng ký / đăng nhập, chat với shop. Dữ liệu chỉ đưa vào DOM bằng textContent.

const $ = id => document.getElementById(id);
let sauId = 0, hen = null, dangGui = false;

async function goi(duong, body) {
  const r = await fetch(duong, body === undefined ? {} : {method: "POST",
    headers: {"Content-Type": "application/json", "X-Man-Hinh-Duyet": "1"}, body: JSON.stringify(body)});
  let d = {};
  try { d = await r.json(); } catch (e) { /* trang lỗi không phải JSON */ }
  if (!r.ok) {
    const e = new Error(r.status === 429 && d.cho_giay ? "Gửi nhanh quá, thử lại sau " + d.cho_giay + " giây" : (d.loi || r.statusText));
    e.status = r.status; throw e;
  }
  return d;
}

/* ---------- đăng nhập / đăng ký ---------- */
function chonTab(dangKy) {
  $("tab-dang-ky").setAttribute("aria-selected", String(dangKy));
  $("tab-dang-nhap").setAttribute("aria-selected", String(!dangKy));
  $("form-dang-ky").hidden = !dangKy; $("form-dang-nhap").hidden = dangKy;
  (dangKy ? $("dk-ten") : $("dn-ten")).focus();
}

async function vao(e, dangKy) {
  e.preventDefault();
  const loi = $(dangKy ? "loi-dang-ky" : "loi-dang-nhap"); loi.textContent = "";
  const nut = e.target.querySelector("button[type=submit]");
  let body;
  if (dangKy) {
    body = {username: $("dk-ten").value.trim(), mat_khau: $("dk-mk").value, nhap_lai: $("dk-mk2").value};
    if (body.mat_khau.length < 6) { loi.textContent = "Mật khẩu ít nhất 6 ký tự"; return; }
    if (body.mat_khau !== body.nhap_lai) { loi.textContent = "Mật khẩu nhập lại không khớp"; $("dk-mk2").focus(); return; }
  } else {
    body = {username: $("dn-ten").value.trim(), mat_khau: $("dn-mk").value};
  }
  nut.disabled = true;
  try { batDau(await goi(dangKy ? "/api/dang-ky" : "/api/dang-nhap", body)); }
  catch (err) { loi.textContent = err.message; }
  finally { nut.disabled = false; }
}

function batDau(toi) {
  if (toi.vai === "shop") {  // shop dùng màn hình duyệt
    $("xin-chao").replaceChildren("Đang đăng nhập tài khoản shop. ", Object.assign(document.createElement("a"), {href: "/", textContent: "Mở màn hình duyệt"}));
    $("man-vao").hidden = true; $("dang-xuat").hidden = false; return;
  }
  $("xin-chao").textContent = "Xin chào, " + toi.username;
  $("man-vao").hidden = true; $("man-chat").hidden = false; $("dang-xuat").hidden = false;
  $("o-tin").focus();
  taiTin();
}

function veVao() {
  clearTimeout(hen); sauId = 0;
  $("ds-tin").replaceChildren();
  $("man-chat").hidden = true; $("man-vao").hidden = false; $("dang-xuat").hidden = true;
  $("xin-chao").textContent = "Bản demo nhóm J97";
}

/* ---------- chat ---------- */
const NHAN = {khach: "Bạn", bot: "Shop", shop: "Shop", he_thong: ""};
function veTin(t) {
  const li = document.createElement("li");
  li.className = "tin tin--" + t.nguoi_noi;
  if (t.nguoi_noi !== "he_thong") {
    const ai = document.createElement("span"); ai.className = "ai-noi";
    ai.textContent = NHAN[t.nguoi_noi] || "";
    if (t.nguoi_noi === "bot") { const n = document.createElement("span"); n.className = "nhan-tu-dong"; n.textContent = "tự động"; ai.append(" ", n); }
    li.append(ai);
  }
  const nd = document.createElement("p"); nd.className = "noi-dung"; nd.textContent = t.noi_dung;
  li.append(nd);
  return li;
}

async function taiTin() {
  clearTimeout(hen);
  try {
    const d = await goi("/api/chat?sau=" + sauId);
    if (d.tin.length) {
      const ds = $("ds-tin"), cuoi = ds.scrollHeight - ds.scrollTop - ds.clientHeight < 40;
      for (const t of d.tin) { ds.append(veTin(t)); sauId = Math.max(sauId, t.id); }
      if (cuoi || d.tin.some(t => t.nguoi_noi === "khach")) ds.scrollTop = ds.scrollHeight;
    }
    $("dang-soan").hidden = !d.dang_soan;
  } catch (err) {
    if (err.status === 401) { veVao(); return; }
  }
  hen = setTimeout(taiTin, 2000);
}

async function gui(e) {
  e.preventDefault();
  const o = $("o-tin"), tin = o.value.trim();
  if (!tin || dangGui) return;
  dangGui = true; $("nut-gui").disabled = true; $("loi-gui").textContent = "";
  try { await goi("/api/chat/gui", {tin}); o.value = ""; await taiTin(); }
  catch (err) { if (err.status === 401) veVao(); else $("loi-gui").textContent = err.message; }
  finally { dangGui = false; $("nut-gui").disabled = false; o.focus(); }
}

/* ---------- gắn sự kiện ---------- */
$("tab-dang-nhap").addEventListener("click", () => chonTab(false));
$("tab-dang-ky").addEventListener("click", () => chonTab(true));
$("form-dang-nhap").addEventListener("submit", e => vao(e, false));
$("form-dang-ky").addEventListener("submit", e => vao(e, true));
$("form-gui").addEventListener("submit", gui);
$("o-tin").addEventListener("keydown", e => { if (e.key === "Enter" && !e.shiftKey && !e.isComposing) gui(e); });
$("dang-xuat").addEventListener("click", async () => { try { await goi("/api/dang-xuat", {}); } catch (e) { /* vẫn về màn đăng nhập */ } veVao(); });

goi("/api/toi").then(batDau).catch(() => veVao());
