// Catatan & Pengingat — CRUD + render + filter kategori (vanilla JS).
(function () {
  "use strict";

  var allNotes = [];
  var editingId = null;
  var catFilter = ""; // "" = semua kategori
  var expanded = {};  // id catatan yang isinya sedang dibuka penuh
  var onDesktop = {}; // id catatan yang sedang tampil sebagai sticky di desktop
  var desktop = false; // jendela aplikasi (pywebview), bukan browser biasa
  var chan = "BroadcastChannel" in window ? new BroadcastChannel("dailyapp-notes") : null;

  function deskApi() { return window.pywebview && window.pywebview.api; }
  function detectDesktop() {
    var a = deskApi();
    desktop = !!(a && a.sticky_open);
    document.body.classList.toggle("desktop-mode", desktop);
    var tip = document.getElementById("stickyTip");
    if (tip) tip.hidden = !desktop;
  }
  function tell(type, id) { if (chan) chan.postMessage({ type: type, id: id }); }

  var CATS = window.CATEGORIES || [];
  var CAT_BY_ID = {};
  CATS.forEach(function (c) { CAT_BY_ID[c.id] = c; });
  var DEFAULT_CAT = (CATS[0] && CATS[0].id) || "umum";

  // Peta warna kategori -> kelas Tailwind (string literal agar pasti ter-generate).
  // Kategori dibedakan oleh ikon, bukan warna: warna (merah/kuning/hijau) khusus untuk status
  // jatuh tempo (DESIGN.md, palet). Kunci "color" di config tetap dibaca agar data lama aman.
  var NEUTRAL_CHIP = "bg-slate-100 text-slate-700";
  var CAT_CHIP = {};

  var $ = function (id) { return document.getElementById(id); };

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function parseDueLocal(due) {
    if (!due) return null;
    var datePart = String(due).trim().split("T")[0];
    var p = datePart.split("-");
    if (p.length !== 3) return null;
    var y = +p[0], m = +p[1], d = +p[2];
    if (!y || !m || !d) return null;
    return new Date(y, m - 1, d);
  }

  function daysFromToday(due) {
    var dd = parseDueLocal(due);
    if (!dd) return null;
    var t = new Date();
    var today = new Date(t.getFullYear(), t.getMonth(), t.getDate());
    return Math.round((dd - today) / 86400000);
  }

  var STATUS = {
    overdue:   { border: "border-l-4 border-red-500",    badge: "bg-red-100 text-red-700" },
    today:     { border: "border-l-4 border-amber-500",  badge: "bg-amber-100 text-amber-700" },
    soon:      { border: "border-l-4 border-yellow-400", badge: "bg-yellow-100 text-yellow-700" },
    scheduled: { border: "border-l-4 border-slate-300",  badge: "bg-slate-100 text-slate-600" },
    none:      { border: "",                              badge: "" },
    done:      { border: "",                              badge: "bg-slate-100 text-slate-600" }
  };

  function dueLabel(note) {
    if (!note.due) return "";
    var diff = daysFromToday(note.due);
    var human;
    if (note.done) human = "Tenggat " + note.due;
    else if (diff === null) human = note.due;
    else if (diff < 0) human = "Lewat " + (-diff) + " hari (" + note.due + ")";
    else if (diff === 0) human = "Jatuh tempo hari ini (" + note.due + ")";
    else human = diff + " hari lagi (" + note.due + ")";
    if (!note.done && note.remind_before_days)
      human += " · ingatkan H-" + note.remind_before_days;
    return human;
  }

  function catMeta(id) {
    return CAT_BY_ID[id] || CAT_BY_ID[DEFAULT_CAT] || { label: "Umum", icon: "notes", color: "slate" };
  }
  function chipCls(color) { return CAT_CHIP[color] || NEUTRAL_CHIP; }
  function noteCat(n) { return CAT_BY_ID[n.category] ? n.category : DEFAULT_CAT; }

  function cardHtml(n) {
    var meta = STATUS[n.status] || STATUS.none;
    var cat = catMeta(n.category);
    var titleCls = n.done ? "line-through text-slate-500" : "text-slate-900";
    var catChip = '<span class="inline-flex items-center gap-1 text-[11px] font-medium rounded px-1.5 py-0.5 ' + chipCls(cat.color) + '">' + DailyIcon(cat.icon || "notes") + " " + esc(cat.label) + "</span>";
    var due = dueLabel(n);
    var dueChip = due
      ? '<span class="text-xs font-medium rounded-full px-2 py-0.5 ' + (meta.badge || "bg-slate-100 text-slate-600") + '">' + esc(due) + "</span>"
      : "";
    var tags = (n.tags || []).map(function (t) {
      return '<span class="inline-block max-w-full break-all text-[11px] bg-slate-100 text-slate-600 rounded px-1.5 py-0.5">#' + esc(t) + "</span>";
    }).join(" ");
    var body = "";
    if (n.body) {
      // Isi dianggap panjang bila lebih dari ~2 baris: kartu menampilkan pratinjau saja.
      var long = n.body.length > 140 || (n.body.match(/\n/g) || []).length >= 2;
      var open = !!expanded[n.id];
      body = '<p id="nb-' + n.id + '" class="text-sm text-slate-600 mt-1 whitespace-pre-wrap break-words' +
        (long && !open ? " line-clamp-2" : "") + '">' + esc(n.body) + "</p>";
      if (long) {
        body += '<button type="button" data-action="toggle" data-id="' + n.id + '" aria-expanded="' + open +
          '" aria-controls="nb-' + n.id + '" class="mt-1 inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:underline">' +
          (open ? "Tutup" : "Selengkapnya") + " " + DailyIcon(open ? "chevron-up" : "chevron-down") + "</button>";
      }
    }
    var pin = n.pinned ? '<span class="text-blue-700" title="Disematkan">' + DailyIcon("pin") + '<span class="sr-only">Disematkan</span></span> ' : "";
    var stuck = desktop && !!onDesktop[n.id];
    var deskChip = stuck
      ? '<span class="inline-flex items-center gap-1 text-[11px] font-medium rounded px-1.5 py-0.5 bg-blue-100 text-blue-700">' + DailyIcon("note") + " Di desktop</span>"
      : "";
    var stickyBtn = desktop
      ? '<button data-action="sticky" data-id="' + n.id + '" aria-pressed="' + stuck + '" title="' + (stuck ? "Lepas dari desktop" : "Tempel ke desktop") + '" aria-label="Tempel ke desktop" class="text-xs px-2 py-1 rounded border ' + (stuck ? "bg-ps text-ps-on border-ps" : "border-slate-300 hover:bg-slate-50") + '">' + DailyIcon("note") + "</button>"
      : "";
    var grip = desktop
      ? '<span class="note-grip" data-drag-handle title="Seret keluar jendela untuk menempel di desktop" aria-hidden="true">' + DailyIcon("grip-vertical") + "</span>"
      : "";
    return '' +
      '<div id="note-' + n.id + '" data-note="' + n.id + '" tabindex="-1" class="note-card bg-white rounded-lg border border-slate-200 ' + meta.border + ' p-4">' +
        '<div class="flex items-start justify-between gap-3">' +
          '<div class="min-w-0 flex-1">' +
            '<h3 class="font-semibold ' + titleCls + ' break-words">' + grip + pin + esc(n.title || "(tanpa judul)") + "</h3>" +
            body +
            '<div class="flex flex-wrap items-center gap-2 mt-2">' + catChip + " " + dueChip + " " + deskChip + " " + tags + "</div>" +
          "</div>" +
          '<div class="flex flex-col items-end gap-1 shrink-0">' +
            '<button data-action="done" data-id="' + n.id + '" class="text-xs px-2 py-1 rounded border border-slate-300 hover:bg-slate-50">' + (n.done ? DailyIcon("arrow-back-up") + " Batalkan" : DailyIcon("check") + " Selesai") + "</button>" +
            '<div class="flex gap-1">' +
              stickyBtn +
              '<button data-action="pin" data-id="' + n.id + '" title="' + (n.pinned ? "Lepas sematan" : "Sematkan") + '" aria-label="' + (n.pinned ? "Lepas sematan" : "Sematkan") + '" class="text-xs px-2 py-1 rounded border border-slate-300 hover:bg-slate-50">' + DailyIcon(n.pinned ? "pinned-off" : "pin") + "</button>" +
              '<button data-action="edit" data-id="' + n.id + '" title="Edit" aria-label="Edit catatan" class="text-xs px-2 py-1 rounded border border-slate-300 hover:bg-slate-50">' + DailyIcon("pencil") + '</button>' +
              '<button data-action="del" data-id="' + n.id + '" title="Hapus" aria-label="Hapus catatan" class="text-xs px-2 py-1 rounded border border-red-200 text-red-600 hover:bg-red-50">' + DailyIcon("trash") + '</button>' +
            "</div>" +
          "</div>" +
        "</div>" +
      "</div>";
  }

  function updateCounts(c) {
    c = c || {};
    function setChip(id, n, text) {
      var el = $(id);
      if (!el) return;
      if (n > 0) { el.textContent = text.replace("{n}", n); el.classList.remove("hidden"); }
      else el.classList.add("hidden");
    }
    setChip("c-overdue", c.overdue, "{n} lewat tempo");
    setChip("c-today", c.today, "{n} hari ini");
    setChip("c-soon", c.soon, "{n} akan datang");
  }

  function populateTags() {
    var sel = $("tagFilter");
    if (!sel) return;
    var current = sel.value;
    var tags = [];
    allNotes.forEach(function (n) {
      (n.tags || []).forEach(function (t) { if (tags.indexOf(t) < 0) tags.push(t); });
    });
    tags.sort(function (a, b) { return a.toLowerCase().localeCompare(b.toLowerCase()); });
    sel.innerHTML = '<option value="">Semua tag</option>' +
      tags.map(function (t) { return '<option value="' + esc(t) + '">#' + esc(t) + "</option>"; }).join("");
    sel.value = current;
  }

  function chipBtn(id, label, glyph, count, active) {
    var cls = active
      ? "bg-ps text-ps-on border-ps"
      : "bg-white text-slate-600 border-slate-300 hover:bg-slate-50";
    return '<button type="button" data-cat="' + id + '" aria-pressed="' + active + '" class="inline-flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-full border ' + cls + '">' +
      (glyph ? DailyIcon(glyph) + " " : "") + esc(label) + " (" + count + ")</button>";
  }

  function renderCatFilter() {
    var el = $("catFilter");
    if (!el) return;
    var counts = {};
    allNotes.forEach(function (n) { var id = noteCat(n); counts[id] = (counts[id] || 0) + 1; });
    var html = chipBtn("", "Semua", "", allNotes.length, catFilter === "");
    CATS.forEach(function (c) {
      html += chipBtn(c.id, c.label, c.icon, counts[c.id] || 0, catFilter === c.id);
    });
    el.innerHTML = html;
  }

  function render() {
    var q = ($("q").value || "").toLowerCase().trim();
    var tag = $("tagFilter").value;
    var showDone = $("showDone").checked;
    var list = allNotes.filter(function (n) {
      if (!showDone && n.done) return false;
      if (catFilter && noteCat(n) !== catFilter) return false;
      if (tag && (n.tags || []).indexOf(tag) < 0) return false;
      if (q) {
        var hay = (n.title + " " + n.body + " " + (n.tags || []).join(" ")).toLowerCase();
        if (hay.indexOf(q) < 0) return false;
      }
      return true;
    });
    $("notesList").innerHTML = list.map(cardHtml).join("");
    var empty = $("emptyState");
    empty.classList.toggle("hidden", list.length > 0);
    if (!list.length) {
      empty.innerHTML = allNotes.length
        ? "Tidak ada catatan untuk filter ini."
        : "Belum ada catatan. Klik <b>Tambah Catatan</b> untuk membuat yang pertama.";
    }
  }

  var loaded = false;

  function showListMessage(html) {
    $("emptyState").classList.add("hidden");
    $("notesList").innerHTML =
      '<div class="lg:col-span-2 bg-white rounded-lg p-6 text-center text-slate-600 border border-slate-200" role="status">' + html + "</div>";
  }

  function loadNotes() {
    if (!loaded) showListMessage("Memuat catatan…");
    return fetch("/api/notes").then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    }).then(function (data) {
      // Penanda "Di desktop" dari jendela sticky yang benar-benar terbuka (bukan status file).
      var a = deskApi();
      if (!desktop || !a || !a.open_stickies) return [data, []];
      return a.open_stickies().then(function (ids) { return [data, ids || []]; }, function () { return [data, []]; });
    }).then(function (pair) {
      var data = pair[0];
      loaded = true;
      allNotes = data.notes || [];
      onDesktop = {};
      pair[1].forEach(function (id) { onDesktop[id] = true; });
      updateCounts(data.counts);
      populateTags();
      renderCatFilter();
      render();
      focusFromHash();
    }).catch(function () {
      if (loaded) { toast("Gagal memuat ulang catatan. Coba muat ulang halaman."); return; }
      showListMessage('Gagal memuat catatan. Pastikan Daily App masih berjalan, lalu ' +
        '<button type="button" data-retry class="underline text-blue-700">coba lagi</button>.');
    });
  }

  function resetForm() {
    editingId = null;
    $("f-id").value = "";
    $("f-title").value = "";
    $("f-body").value = "";
    $("f-category").value = DEFAULT_CAT;
    $("f-tags").value = "";
    $("f-due").value = "";
    $("f-lead").value = "7";
    $("f-pinned").checked = false;
    $("formMsg").textContent = "";
  }

  function openForm() {
    $("noteForm").classList.remove("hidden");
    $("btnNew").classList.add("hidden");
  }
  function closeForm() {
    $("noteForm").classList.add("hidden");
    $("btnNew").classList.remove("hidden");
    resetForm();
  }

  function newNote() {
    resetForm();
    $("formTitle").textContent = "Catatan baru";
    $("btnSave").textContent = "Simpan";
    openForm();
    $("f-title").focus();
  }

  // Nilai form saat Edit dibuka: hanya kolom yang diubah yang dikirim, agar perubahan dari
  // sticky di desktop (judul/isi) tidak tertimpa nilai lama di form.
  var editSnapshot = null;

  function formValues() {
    return {
      title: $("f-title").value,
      body: $("f-body").value,
      category: $("f-category").value,
      tags: $("f-tags").value.split(",").map(function (t) { return t.trim(); }).filter(Boolean).join(","),
      due: $("f-due").value,
      remind_before_days: String($("f-lead").value),
      pinned: $("f-pinned").checked
    };
  }

  function startEdit(n) {
    editingId = n.id;
    $("f-id").value = n.id;
    $("f-title").value = n.title || "";
    $("f-body").value = n.body || "";
    $("f-category").value = noteCat(n);
    $("f-tags").value = (n.tags || []).join(", ");
    $("f-due").value = n.due ? String(n.due).split("T")[0] : "";
    $("f-lead").value = (n.remind_before_days != null ? n.remind_before_days : 7);
    $("f-pinned").checked = !!n.pinned;
    $("formTitle").textContent = "Edit catatan";
    $("btnSave").textContent = "Perbarui";
    editSnapshot = formValues();
    openForm();
    window.scrollTo({ top: 0, behavior: "smooth" });
    $("f-title").focus();
  }

  function toast(msg) {
    var t = document.createElement("div");
    t.textContent = msg;
    t.className = "fixed bottom-4 right-4 bg-slate-800 text-white text-sm px-4 py-2 rounded-md shadow-lg z-50";
    document.body.appendChild(t);
    setTimeout(function () { t.remove(); }, 2000);
  }

  function submitForm(e) {
    e.preventDefault();
    var payload = {
      title: $("f-title").value,
      body: $("f-body").value,
      category: $("f-category").value,
      tags: $("f-tags").value,
      due: $("f-due").value,
      remind_before_days: $("f-lead").value,
      pinned: $("f-pinned").checked
    };
    if (!payload.title.trim() && !payload.body.trim()) {
      $("formMsg").textContent = "Judul atau isi tidak boleh kosong.";
      return;
    }
    var wasEdit = !!editingId;
    if (wasEdit && editSnapshot) {
      var now = formValues();
      Object.keys(payload).forEach(function (k) { if (now[k] === editSnapshot[k]) delete payload[k]; });
      if (!Object.keys(payload).length) { closeForm(); return; }
    }
    var url = wasEdit ? "/api/notes/" + editingId : "/api/notes";
    fetch(url, {
      method: wasEdit ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).then(function (r) {
      if (!r.ok) throw new Error("Gagal menyimpan");
      return r.json();
    }).then(function (saved) {
      closeForm();
      toast(wasEdit ? "Catatan diperbarui" : "Catatan disimpan");
      if (wasEdit && saved) tell("changed", saved.id);
      loadNotes();
    }).catch(function (err) { $("formMsg").textContent = err.message; });
  }

  function patch(id, data, msg) {
    return fetch("/api/notes/" + id, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    }).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      if (msg) toast(msg);
      tell("changed", id);
      return loadNotes();
    }).catch(function () { toast("Gagal memperbarui catatan. Coba lagi."); });
  }

  // ---- Sticky note di desktop (hanya di jendela aplikasi) ----
  function stickyResult(r) {
    if (r && r.ok === false) toast(r.error || "Sticky gagal dibuat.");
    else if (!(r && r.already)) toast("Ditempel di desktop");
    loadNotes();
  }

  function toggleSticky(id) {
    var a = deskApi();
    if (!a) return;
    if (onDesktop[id]) {
      a.sticky_close(id).then(function () { toast("Dilepas dari desktop"); loadNotes(); });
    } else {
      a.sticky_open(id).then(stickyResult, function () { toast("Sticky gagal dibuat."); });
    }
  }

  // Seret kartu sampai keluar jendela: sticky muncul di bawah kursor dan ikut terseret.
  var drag = null;

  function onCardPointerDown(e) {
    if (!desktop || e.button !== 0 || e.pointerType === "touch") return;
    // Seret dari pegangan atau area kosong kartu; dari teks tetap bisa menyeleksi teks.
    if (!e.target.closest("[data-drag-handle]") &&
        e.target.closest("h3, p, span, button, a, input, textarea, select, label")) return;
    var card = e.target.closest("[data-note]");
    if (!card) return;
    drag = { id: card.getAttribute("data-note"), card: card, x: e.clientX, y: e.clientY, pid: e.pointerId, active: false };
    try { card.setPointerCapture(e.pointerId); } catch (_) { /* tetap jalan tanpa capture */ }
  }

  function endDrag() {
    if (!drag) return;
    try { drag.card.releasePointerCapture(drag.pid); } catch (_) { /* sudah dilepas */ }
    drag.card.style.transform = "";
    drag.card.classList.remove("note-dragging");
    document.body.classList.remove("is-dragging-note");
    $("dragHint").hidden = true;
    drag = null;
  }

  function tearOff() {
    if (!drag || !drag.active) return;
    var id = drag.id;
    endDrag();
    var a = deskApi();
    if (a) a.sticky_tear(id).then(stickyResult, function () { toast("Sticky gagal dibuat."); });
  }

  function onPointerMove(e) {
    if (!drag || e.pointerId !== drag.pid) return;
    if (!(e.buttons & 1)) { endDrag(); return; } // tombol dilepas tanpa pointerup (mis. Alt+Tab)
    var dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    if (!drag.active) {
      if (Math.abs(dx) + Math.abs(dy) < 8) return;
      drag.active = true;
      var sel = window.getSelection();
      if (sel) sel.removeAllRanges();
      drag.card.classList.add("note-dragging");
      document.body.classList.add("is-dragging-note");
      $("dragHint").hidden = false;
    }
    drag.card.style.transform = "translate(" + dx + "px," + dy + "px) rotate(2deg)";
    if (e.clientX <= 0 || e.clientY <= 0 || e.clientX >= window.innerWidth - 1 || e.clientY >= window.innerHeight - 1) {
      tearOff();
    }
  }

  function focusFromHash() {
    var m = /^#note-([0-9a-f]+)$/.exec(location.hash || "");
    if (!m) return;
    history.replaceState(null, "", location.pathname);
    var el = document.getElementById("note-" + m[1]);
    if (!el && allNotes.some(function (n) { return n.id === m[1]; })) {
      // Kartunya tersaring: tampilkan semua dulu.
      catFilter = "";
      $("q").value = "";
      $("tagFilter").value = "";
      $("showDone").checked = true;
      renderCatFilter();
      render();
      el = document.getElementById("note-" + m[1]);
    }
    if (!el) return;
    el.scrollIntoView({ block: "center" });
    el.focus({ preventScroll: true });
    el.classList.add("note-flash");
    setTimeout(function () { el.classList.remove("note-flash"); }, 2200);
  }

  var reloadTimer = null;
  function reloadSoon() {
    clearTimeout(reloadTimer);
    reloadTimer = setTimeout(loadNotes, 250);
  }

  function onListClick(e) {
    if (e.target.closest("[data-retry]")) { loadNotes(); return; }
    var btn = e.target.closest("button[data-action]");
    if (!btn) return;
    var id = btn.getAttribute("data-id");
    var action = btn.getAttribute("data-action");
    var note = allNotes.filter(function (n) { return n.id === id; })[0];
    if (!note) return;
    if (action === "done") patch(id, { done: !note.done }, note.done ? "Dibuka kembali" : "Ditandai selesai");
    else if (action === "pin") patch(id, { pinned: !note.pinned });
    else if (action === "sticky") toggleSticky(id);
    else if (action === "edit") startEdit(note);
    else if (action === "toggle") {
      expanded[id] = !expanded[id];
      render();
      var again = document.querySelector('#notesList button[data-action="toggle"][data-id="' + id + '"]');
      if (again) again.focus();
    }
    else if (action === "del") {
      if (confirm("Hapus catatan ini?")) {
        fetch("/api/notes/" + id, { method: "DELETE" }).then(function (r) {
          if (!r.ok) throw new Error("HTTP " + r.status);
          toast("Catatan dihapus");
          tell("deleted", id);
          loadNotes();
        }).catch(function () { toast("Gagal menghapus catatan. Coba lagi."); });
      }
    }
  }

  function onCatClick(e) {
    var btn = e.target.closest("button[data-cat]");
    if (!btn) return;
    catFilter = btn.getAttribute("data-cat");
    renderCatFilter();
    render();
  }

  document.addEventListener("DOMContentLoaded", function () {
    $("noteForm").addEventListener("submit", submitForm);
    $("btnNew").addEventListener("click", newNote);
    $("btnCancel").addEventListener("click", closeForm);
    $("btnClose").addEventListener("click", closeForm);
    $("notesList").addEventListener("click", onListClick);
    $("catFilter").addEventListener("click", onCatClick);
    $("q").addEventListener("input", render);
    $("tagFilter").addEventListener("change", render);
    $("showDone").addEventListener("change", render);
    $("notesList").addEventListener("pointerdown", onCardPointerDown);
    document.addEventListener("pointermove", onPointerMove);
    document.addEventListener("pointerup", function (e) { if (drag && e.pointerId === drag.pid) endDrag(); });
    document.addEventListener("pointercancel", endDrag);
    window.addEventListener("blur", endDrag);
    // Esc membatalkan seret (didaftarkan di fase capture agar tidak sampai ke Esc → Beranda).
    window.addEventListener("keydown", function (e) {
      if (drag && e.key === "Escape") { endDrag(); e.preventDefault(); e.stopPropagation(); }
    }, true);
    // Cadangan bila WebView2 tidak meneruskan gerakan di luar jendela: keluar = sobek.
    document.documentElement.addEventListener("mouseleave", function () { if (drag && drag.active) tearOff(); });
    window.addEventListener("hashchange", focusFromHash);
    if (chan) chan.onmessage = function (ev) {
      var m = ev.data || {};
      if (m.type === "changed" || m.type === "sticky") reloadSoon();
    };
    detectDesktop();
    window.addEventListener("pywebviewready", function () { detectDesktop(); render(); });
    loadNotes();
  });
})();
