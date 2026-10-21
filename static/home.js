// Beranda gaya konsol: rail tile (panah kiri/kanan + Enter), sorotan, dan ringkasan data nyata.
(function () {
  "use strict";

  var $ = function (id) { return document.getElementById(id); };
  var LAST = "dailyapp:lastTile";
  var rail = $("rail");
  if (!rail) return;
  var tiles = Array.prototype.slice.call(rail.querySelectorAll(".tile"));
  var current = null;

  function esc(s) {
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
  function sound(kind) { if (window.DailySound) window.DailySound.play(kind); }

  function spotlight(tile) {
    if (!tile || tile === current) return;
    current = tile;
    tiles.forEach(function (t) { t.classList.toggle("is-focus", t === tile); });
    $("spot-title").textContent = tile.dataset.title;
    $("spot-desc").textContent = tile.dataset.desc;
    $("spot-open").href = tile.getAttribute("href");
    var bd = $("backdrop");
    if (bd && tile.dataset.hue) bd.style.setProperty("--spot", tile.dataset.hue);
    var chips = [];
    try { chips = JSON.parse(tile.dataset.chips || "[]"); } catch (e) { /* abaikan */ }
    $("spot-chips").innerHTML = chips.map(function (c) {
      return '<span class="text-xs text-slate-600 border border-slate-300 rounded px-2 py-1">' + esc(c) + "</span>";
    }).join("");
    var setup = $("spot-setup");
    setup.classList.toggle("hidden", !tile.dataset.setup);
    setup.querySelector("span").textContent = tile.dataset.setup ? "Perlu setup: " + tile.dataset.setup : "";
  }

  function remember(tile) {
    try { sessionStorage.setItem(LAST, tile.dataset.id); } catch (e) { /* abaikan */ }
  }

  rail.addEventListener("focusin", function (ev) {
    var tile = ev.target.closest(".tile");
    if (tile && tile !== current) { spotlight(tile); sound("move"); }
  });
  // Kursor mengarah ke tile lain: sorotan ikut pindah + bunyi berpindah (sekali per tile).
  rail.addEventListener("mouseover", function (ev) {
    var tile = ev.target.closest(".tile");
    if (tile && tile !== current) { spotlight(tile); sound("move"); }
  });
  rail.addEventListener("click", function (ev) {
    var tile = ev.target.closest(".tile");
    if (tile) { remember(tile); sound("select"); }
  });
  $("spot-open").addEventListener("click", function () {
    if (current) remember(current);
    sound("select");
  });

  rail.addEventListener("keydown", function (ev) {
    var i = tiles.indexOf(document.activeElement);
    if (i < 0) return;
    var next = null;
    if (ev.key === "ArrowRight") next = tiles[Math.min(tiles.length - 1, i + 1)];
    else if (ev.key === "ArrowLeft") next = tiles[Math.max(0, i - 1)];
    else if (ev.key === "Home") next = tiles[0];
    else if (ev.key === "End") next = tiles[tiles.length - 1];
    if (!next) return;
    ev.preventDefault();
    // Sorotan diperbarui langsung: event focusin bisa tertunda bila jendela tidak aktif.
    if (next !== current) { spotlight(next); sound("move"); }
    next.focus();
    next.scrollIntoView({ block: "nearest", inline: "nearest" });
  });

  // Kembali dari halaman lain: fokus ke tile yang terakhir dibuka.
  var lastId = null;
  try { lastId = sessionStorage.getItem(LAST); } catch (e) { /* abaikan */ }
  var start = tiles.filter(function (t) { return t.dataset.id === lastId; })[0] || tiles[0];
  if (start) {
    spotlight(start);
    start.focus({ preventScroll: true });
    start.scrollIntoView({ block: "nearest", inline: "nearest" });
  }

  // ---- Ringkasan (data nyata) ----
  function rp(n) { return "Rp " + Math.round(n).toLocaleString("id-ID"); }

  fetch("/api/notes/due").then(function (r) {
    if (!r.ok) throw new Error();
    return r.json();
  }).then(function (d) {
    var el = $("sum-notes");
    if (!d.overdue && !d.today && !d.soon) {
      el.textContent = "Tidak ada yang jatuh tempo dalam waktu dekat.";
      return;
    }
    var parts = [];
    if (d.overdue) parts.push('<span class="text-red-700 font-semibold">' + d.overdue + " lewat tempo</span>");
    if (d.today) parts.push('<span class="text-amber-700 font-semibold">' + d.today + " hari ini</span>");
    if (d.soon) parts.push(d.soon + " akan datang");
    var items = (d.items || []).slice(0, 3).map(function (it) {
      return '<li class="truncate">' + esc(it.title) + "</li>";
    }).join("");
    el.innerHTML = parts.join(" · ") + (items ? '<ul class="mt-2 space-y-1 text-slate-700">' + items + "</ul>" : "");
  }).catch(function () {
    $("sum-notes").textContent = "Gagal memuat pengingat. Muat ulang halaman untuk mencoba lagi.";
  });

  fetch("/api/invoice/state").then(function (r) {
    if (!r.ok) throw new Error();
    return r.json();
  }).then(function (d) {
    var el = $("sum-invoice");
    if (!d.brands.length) { el.textContent = "Belum ada brand. Buka Invoice untuk membuat brand pertama."; return; }
    if (!d.invoices.length) { el.textContent = "Belum ada invoice."; return; }
    var unpaid = d.invoices.filter(function (i) { return i.effective_status !== "paid"; });
    var overdue = unpaid.filter(function (i) { return i.effective_status === "overdue"; }).length;
    if (!unpaid.length) { el.textContent = "Semua " + d.invoices.length + " invoice sudah lunas."; return; }
    var sum = unpaid.reduce(function (a, i) { return a + i.totals.total; }, 0);
    el.innerHTML = '<span class="text-slate-900 font-semibold text-base">' + rp(sum) + "</span> dari " +
      unpaid.length + " invoice" + (overdue ? ' · <span class="text-red-700 font-semibold">' + overdue + " lewat jatuh tempo</span>" : "");
  }).catch(function () {
    $("sum-invoice").textContent = "Gagal memuat invoice. Muat ulang halaman untuk mencoba lagi.";
  });
})();
