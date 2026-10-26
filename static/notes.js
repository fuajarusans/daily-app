// Catatan & Pengingat — CRUD + render + filter, checklist, arsip, urungkan (vanilla JS).
(function () {
  "use strict";

  var allNotes = [];
  var allArchived = [];
  var archiveView = false; // sedang melihat arsip
  var editingId = null;
  var catFilter = ""; // "" = semua kategori
  var expanded = {};  // id catatan yang isinya sedang dibuka penuh
  var clOpen = {};    // id catatan yang checklist panjangnya sedang dibuka penuh
  var addOpen = {};   // catatan tanpa checklist yang kolom "Tambah item"-nya sedang dibuka
  var askDone = {};   // catatan yang sedang menawarkan "tandai selesai?" (semua item dicentang)
  var onDesktop = {}; // id catatan yang sedang tampil sebagai sticky di desktop
  var desktop = false; // jendela aplikasi (pywebview), bukan browser biasa
  var chan = "BroadcastChannel" in window ? new BroadcastChannel("dailyapp-notes") : null;
  var ctl = null;     // kendali checklist (static/checklist.js)
  var deferredReload = false;
  var pendingFocus = null; // id kartu yang difokus setelah dimuat ulang ("" = tombol utama)
  var doneBusy = {};       // tombol Selesai yang permintaannya masih berjalan (cegah klik ganda)

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
  var PRIO_LABEL = {};
  (window.PRIORITIES || []).forEach(function (p) { PRIO_LABEL[p.id] = p.label; });
  var RECUR_LABEL = {};
  (window.RECURRENCES || []).forEach(function (r) { RECUR_LABEL[r.id] = r.label; });

  // Peta warna kategori -> kelas Tailwind (string literal agar pasti ter-generate).
  // Kategori dibedakan oleh ikon, bukan warna: warna (merah/kuning/hijau) khusus untuk status
  // jatuh tempo (DESIGN.md, palet). Kunci "color" di config tetap dibaca agar data lama aman.
  var NEUTRAL_CHIP = "bg-slate-100 text-slate-700";
  var CAT_CHIP = {};
  // Prioritas: hanya "tinggi" yang berwarna (ungu, tidak dipakai status); lainnya chip netral.
  var PRIO_CHIP = { tinggi: "bg-purple-100 text-purple-700" };
  var CHIP = "inline-flex items-center gap-1 text-[11px] font-medium rounded px-1.5 py-0.5 ";
  var ICON_BTN = "text-xs px-2 py-1 rounded border border-slate-300 hover:bg-slate-50";

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

  function fmtDate(due) {
    var d = parseDueLocal(due);
    return d ? d.toLocaleDateString("id-ID", { weekday: "short", day: "numeric", month: "short" }) : String(due || "");
  }

  function todayIso() {
    var t = new Date();
    return t.getFullYear() + "-" + ("0" + (t.getMonth() + 1)).slice(-2) + "-" + ("0" + t.getDate()).slice(-2);
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

  function findNote(id) {
    var lists = [allNotes, allArchived];
    for (var l = 0; l < lists.length; l++)
      for (var i = 0; i < lists[l].length; i++) if (lists[l][i].id === id) return lists[l][i];
    return null;
  }
  function setNote(n) {
    [allNotes, allArchived].forEach(function (list) {
      for (var i = 0; i < list.length; i++) if (list[i].id === n.id) list[i] = n;
    });
  }

  function askHtml(id) {
    return '<div class="cl-ask" role="group" aria-label="Semua item checklist selesai">' + DailyIcon("circle-check") +
      "<span>Semua item selesai. Tandai catatan selesai?</span>" +
      '<span class="flex gap-2"><button type="button" data-action="ask-yes" data-id="' + id + '" class="cl-ask-yes">Ya, tandai selesai</button>' +
      '<button type="button" data-action="ask-no" data-id="' + id + '" class="cl-ask-no">Nanti</button></span></div>';
  }

  // Chip progres checklist; selalu ada (tersembunyi bila kosong) agar bisa diperbarui sendiri.
  function progChipHtml(n) {
    return '<span id="cp-' + n.id + '" class="' + CHIP + NEUTRAL_CHIP + (n.checklist_total ? "" : " hidden") + '">' +
      (n.checklist_total
        ? DailyIcon("list-check") + ' <span class="sr-only">Checklist </span>' + n.checklist_done + "/" + n.checklist_total +
          '<span class="sr-only"> item selesai</span>'
        : "") + "</span>";
  }

  function cardHtml(n) {
    var arch = !!n.archived;
    var meta = arch ? STATUS.none : (STATUS[n.status] || STATUS.none);
    var cat = catMeta(n.category);
    var titleCls = n.done ? "line-through text-slate-500" : "text-slate-900";
    var catChip = '<span class="' + CHIP + chipCls(cat.color) + '">' + DailyIcon(cat.icon || "notes") + " " + esc(cat.label) + "</span>";
    var prioChip = n.priority
      ? '<span class="' + CHIP + (PRIO_CHIP[n.priority] || NEUTRAL_CHIP) + '">' + DailyIcon("flag") + " Prioritas " + esc((PRIO_LABEL[n.priority] || "").toLowerCase()) + "</span>"
      : "";
    var recurChip = n.recurrence
      ? '<span class="' + CHIP + NEUTRAL_CHIP + '" title="Tugas berulang">' + DailyIcon("repeat") + ' <span class="sr-only">Berulang </span>' +
        esc(RECUR_LABEL[n.recurrence] || "") + "</span>"
      : "";
    var progChip = progChipHtml(n);
    var due = arch ? "" : dueLabel(n);
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
    var checklist = DailyChecklist.html(n, {
      icon: DailyIcon, limit: 8, open: !!clOpen[n.id], readonly: arch, addOpen: !!addOpen[n.id],
      draft: ctl ? ctl.drafts[n.id] : ""
    });
    var ask = !arch && askDone[n.id] && !n.done && DailyChecklist.allDone(n) ? askHtml(n.id) : "";
    var pin = n.pinned && !arch ? '<span class="text-blue-700" title="Disematkan">' + DailyIcon("pin") + '<span class="sr-only">Disematkan</span></span> ' : "";
    var stuck = desktop && !!onDesktop[n.id];
    var deskChip = stuck
      ? '<span class="' + CHIP + 'bg-blue-100 text-blue-700">' + DailyIcon("note") + " Di desktop</span>"
      : "";
    var grip = desktop && !arch
      ? '<span class="note-grip" data-drag-handle title="Seret keluar jendela untuk menempel di desktop" aria-hidden="true">' + DailyIcon("grip-vertical") + "</span>"
      : "";
    var label = esc(n.title || "(tanpa judul)");
    var actions;
    if (arch) {
      actions =
        '<button data-action="unarchive" data-id="' + n.id + '" class="' + ICON_BTN + ' inline-flex items-center gap-1">' + DailyIcon("archive-off") + " Pulihkan</button>" +
        '<button data-action="del" data-id="' + n.id + '" title="Hapus" aria-label="Hapus catatan: ' + label + '" class="text-xs px-2 py-1 rounded border border-red-200 text-red-600 hover:bg-red-50">' + DailyIcon("trash") + "</button>";
    } else {
      var stickyBtn = desktop
        ? '<button data-action="sticky" data-id="' + n.id + '" aria-pressed="' + stuck + '" title="' + (stuck ? "Lepas dari desktop" : "Tempel ke desktop") + '" aria-label="Tempel ke desktop" class="text-xs px-2 py-1 rounded border ' + (stuck ? "bg-ps text-ps-on border-ps" : "border-slate-300 hover:bg-slate-50") + '">' + DailyIcon("note") + "</button>"
        : "";
      var listBtn = !(n.checklist || []).length && !addOpen[n.id]
        ? '<button data-action="checklist" data-id="' + n.id + '" title="Tambah checklist" aria-label="Tambah checklist" class="' + ICON_BTN + '">' + DailyIcon("list-check") + "</button>"
        : "";
      actions =
        '<button data-action="done" data-id="' + n.id + '" class="' + ICON_BTN + '">' + (n.done ? DailyIcon("arrow-back-up") + " Batalkan" : DailyIcon("check") + " Selesai") + "</button>" +
        '<div class="grid grid-cols-3 gap-1">' +
          stickyBtn + listBtn +
          '<button data-action="pin" data-id="' + n.id + '" title="' + (n.pinned ? "Lepas sematan" : "Sematkan") + '" aria-label="' + (n.pinned ? "Lepas sematan" : "Sematkan") + '" class="' + ICON_BTN + '">' + DailyIcon(n.pinned ? "pinned-off" : "pin") + "</button>" +
          '<button data-action="edit" data-id="' + n.id + '" title="Edit" aria-label="Edit catatan" class="' + ICON_BTN + '">' + DailyIcon("pencil") + "</button>" +
          '<button data-action="archive" data-id="' + n.id + '" title="Arsipkan" aria-label="Arsipkan catatan" class="' + ICON_BTN + '">' + DailyIcon("archive") + "</button>" +
          '<button data-action="del" data-id="' + n.id + '" title="Hapus" aria-label="Hapus catatan" class="text-xs px-2 py-1 rounded border border-red-200 text-red-600 hover:bg-red-50">' + DailyIcon("trash") + "</button>" +
        "</div>";
    }
    return '' +
      '<div id="note-' + n.id + '" ' + (arch ? "data-archived" : "data-note") + '="' + n.id + '" tabindex="-1" class="note-card bg-white rounded-lg border border-slate-200 ' + meta.border + ' p-4">' +
        '<div class="flex items-start justify-between gap-3">' +
          '<div class="min-w-0 flex-1">' +
            '<h3 class="font-semibold ' + titleCls + ' break-words">' + grip + pin + label + "</h3>" +
            body + checklist + ask +
            '<div class="flex flex-wrap items-center gap-2 mt-2">' + catChip + " " + prioChip + " " + recurChip + " " + progChip + " " + dueChip + " " + deskChip + " " + tags + "</div>" +
          "</div>" +
          '<div class="flex flex-col items-end gap-1 shrink-0">' + actions + "</div>" +
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

  function source() { return archiveView ? allArchived : allNotes; }

  function populateTags() {
    var sel = $("tagFilter");
    if (!sel) return;
    var current = sel.value;
    var tags = [];
    source().forEach(function (n) {
      (n.tags || []).forEach(function (t) { if (tags.indexOf(t) < 0) tags.push(t); });
    });
    tags.sort(function (a, b) { return a.toLowerCase().localeCompare(b.toLowerCase()); });
    sel.innerHTML = '<option value="">Semua tag</option>' +
      tags.map(function (t) { return '<option value="' + esc(t) + '">#' + esc(t) + "</option>"; }).join("");
    sel.value = tags.indexOf(current) >= 0 ? current : "";
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
    var list = source();
    var counts = {};
    list.forEach(function (n) { var id = noteCat(n); counts[id] = (counts[id] || 0) + 1; });
    var html = chipBtn("", "Semua", "", list.length, catFilter === "");
    CATS.forEach(function (c) {
      html += chipBtn(c.id, c.label, c.icon, counts[c.id] || 0, catFilter === c.id);
    });
    el.innerHTML = html;
  }

  function renderArchiveToggle() {
    var b = $("btnArchive");
    b.setAttribute("aria-pressed", String(archiveView));
    b.className = "inline-flex items-center gap-1.5 text-sm px-3 py-2 rounded-md border " +
      (archiveView ? "bg-ps text-ps-on border-ps" : "border-slate-300 hover:bg-slate-50");
    $("archiveLabel").textContent = "Arsip (" + allArchived.length + ")";
    $("archiveNote").classList.toggle("hidden", !archiveView);
    $("btnNew").classList.toggle("hidden", archiveView || !$("noteForm").classList.contains("hidden"));
  }

  // Kunci fokus yang bisa ditemukan lagi setelah kartu digambar ulang.
  function focusKey(a) {
    var card = a.closest(".note-card");
    if (!card) return null;
    var li = a.closest("[data-cl-item]");
    var sel = null;
    if (a.getAttribute("data-cl")) {
      sel = (li ? '[data-cl-item="' + li.getAttribute("data-cl-item") + '"] ' : "") + '[data-cl="' + a.getAttribute("data-cl") + '"]';
    } else if (a.getAttribute("data-action")) {
      sel = '[data-action="' + a.getAttribute("data-action") + '"]';
    }
    var caret = null;
    try { caret = a.type === "text" ? a.selectionStart : null; } catch (_) { caret = null; }
    return { card: card.id, sel: sel, caret: caret };
  }
  function restoreKey(k) {
    if (!k) return;
    var card = document.getElementById(k.card);
    if (!card) return;
    var el = (k.sel && card.querySelector(k.sel)) || card;
    el.focus({ preventScroll: true });
    if (k.caret != null && el.setSelectionRange) {
      try { el.setSelectionRange(k.caret, k.caret); } catch (_) { /* abaikan */ }
    }
  }
  function activeKey() {
    var a = document.activeElement;
    return a && $("notesList").contains(a) ? focusKey(a) : null;
  }

  function renderCard(id) {
    var el = $("note-" + id);
    var n = findNote(id);
    if (!el || !n) { render(); return; }
    var key = el.contains(document.activeElement) ? focusKey(document.activeElement) : null;
    var tmp = document.createElement("div");
    tmp.innerHTML = cardHtml(n);
    el.parentNode.replaceChild(tmp.firstChild, el);
    if (ctl) ctl.restoreInputs(id);
    restoreKey(key);
  }

  function matches(n, q, tag, prio, showDone) {
    if (!showDone && n.done) return false;
    if (catFilter && noteCat(n) !== catFilter) return false;
    if (tag && (n.tags || []).indexOf(tag) < 0) return false;
    if (prio === "-" ? !!n.priority : (prio && n.priority !== prio)) return false;
    if (q) {
      var items = (n.checklist || []).map(function (i) { return i.text; }).join(" ");
      var hay = (n.title + " " + n.body + " " + (n.tags || []).join(" ") + " " + items).toLowerCase();
      if (hay.indexOf(q) < 0) return false;
    }
    return true;
  }

  function render() {
    var q = ($("q").value || "").toLowerCase().trim();
    var tag = $("tagFilter").value;
    var prio = $("prioFilter").value;
    var showDone = archiveView || $("showDone").checked;
    var src = source();
    var list = src.filter(function (n) { return matches(n, q, tag, prio, showDone); });
    var key = activeKey();
    $("notesList").innerHTML = list.map(cardHtml).join("");
    if (ctl) Object.keys(ctl.texts).forEach(function (id) { ctl.restoreInputs(id); });
    restoreKey(key);
    renderArchiveToggle();
    var empty = $("emptyState");
    empty.classList.toggle("hidden", list.length > 0);
    if (!list.length) {
      if (archiveView) empty.innerHTML = src.length ? "Tidak ada catatan arsip untuk filter ini." : "Arsip kosong.";
      else empty.innerHTML = src.length
        ? "Tidak ada catatan untuk filter ini."
        : "Belum ada catatan. Klik <b>Tambah Catatan</b> untuk membuat yang pertama.";
    }
  }

  var loaded = false;

  // Sasaran fokus bila tidak ada kartu: harus terlihat, dan bukan kolom teks (Ctrl+Z = Urungkan).
  function fallbackFocus() {
    var b = $("btnNew");
    return (archiveView || b.classList.contains("hidden")) ? $("btnArchive") : b;
  }

  function showListMessage(html) {
    $("emptyState").classList.add("hidden");
    $("notesList").innerHTML =
      '<div class="lg:col-span-2 bg-white rounded-lg p-6 text-center text-slate-600 border border-slate-200" role="status">' + html + "</div>";
  }

  function loadNotes() {
    if (!loaded) showListMessage("Memuat catatan…");
    deferredReload = false;
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
      allArchived = data.archived || [];
      onDesktop = {};
      pair[1].forEach(function (id) { onDesktop[id] = true; });
      updateCounts(data.counts);
      populateTags();
      renderCatFilter();
      render();
      if (pendingFocus !== null) {
        var el = (pendingFocus && $("note-" + pendingFocus)) || fallbackFocus();
        pendingFocus = null;
        if (el) el.focus({ preventScroll: false });
      }
      focusFromHash();
    }).catch(function () {
      if (loaded) { toast("Gagal memuat ulang catatan. Coba muat ulang halaman."); return; }
      showListMessage('Gagal memuat catatan. Pastikan Daily App masih berjalan, lalu ' +
        '<button type="button" data-retry class="underline text-blue-700">coba lagi</button>.');
    });
  }

  // ---- Form tambah / edit ----
  function resetForm() {
    editingId = null;
    $("f-id").value = "";
    $("f-title").value = "";
    $("f-body").value = "";
    $("f-checklist").value = "";
    $("f-category").value = DEFAULT_CAT;
    $("f-priority").value = "";
    $("f-tags").value = "";
    $("f-due").value = "";
    $("f-recur").value = "";
    $("f-lead").value = "7";
    $("f-pinned").checked = false;
    $("f-checklist-wrap").classList.remove("hidden");
    $("f-checklist-note").classList.add("hidden");
    $("formMsg").textContent = "";
  }

  function openForm() {
    $("noteForm").classList.remove("hidden");
    $("btnNew").classList.add("hidden");
  }
  function closeForm() {
    $("noteForm").classList.add("hidden");
    $("btnNew").classList.toggle("hidden", archiveView);
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
      priority: $("f-priority").value,
      tags: $("f-tags").value.split(",").map(function (t) { return t.trim(); }).filter(Boolean).join(","),
      due: $("f-due").value,
      recurrence: $("f-recur").value,
      remind_before_days: String($("f-lead").value),
      pinned: $("f-pinned").checked
    };
  }

  // Satu item per baris; baris yang diawali spasi/tab menjadi sub-item.
  function parseChecklist(text) {
    return String(text || "").split(/\r?\n/).filter(function (l) { return l.trim(); }).map(function (l) {
      return { text: l.trim(), level: /^[ \t]/.test(l) ? 1 : 0 };
    });
  }

  function startEdit(n) {
    resetForm();
    editingId = n.id;
    $("f-id").value = n.id;
    $("f-title").value = n.title || "";
    $("f-body").value = n.body || "";
    $("f-category").value = noteCat(n);
    $("f-priority").value = n.priority || "";
    $("f-tags").value = (n.tags || []).join(", ");
    $("f-due").value = n.due ? String(n.due).split("T")[0] : "";
    $("f-recur").value = n.recurrence || "";
    $("f-lead").value = (n.remind_before_days != null ? n.remind_before_days : 7);
    $("f-pinned").checked = !!n.pinned;
    $("f-checklist-wrap").classList.add("hidden");
    $("f-checklist-note").classList.toggle("hidden", !(n.checklist || []).length);
    $("formTitle").textContent = "Edit catatan";
    $("btnSave").textContent = "Perbarui";
    editSnapshot = formValues();
    openForm();
    window.scrollTo({ top: 0, behavior: "smooth" });
    $("f-title").focus();
  }

  function submitForm(e) {
    e.preventDefault();
    var payload = formValues();
    var wasEdit = !!editingId;
    var items = wasEdit ? [] : parseChecklist($("f-checklist").value);
    var hasItems = wasEdit
      ? ((findNote(editingId) || {}).checklist || []).some(function (i) { return i && String(i.text || "").trim(); })
      : items.length > 0;
    if (!payload.title.trim() && !payload.body.trim() && !hasItems) {
      $("formMsg").textContent = "Isi judul, detail, atau checklist terlebih dahulu.";
      return;
    }
    if (wasEdit && editSnapshot) {
      Object.keys(payload).forEach(function (k) { if (payload[k] === editSnapshot[k]) delete payload[k]; });
      if (!Object.keys(payload).length) { closeForm(); return; }
    } else {
      payload.checklist = items;
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
      if (saved) pendingFocus = saved.id;
      loadNotes();
    }).catch(function (err) { $("formMsg").textContent = err.message; });
  }

  // ---- Toast (satu wilayah live) dengan tombol Urungkan ----
  // Waktu tampil berhenti selama toast disorot atau difokus; saat hilang, fokus dikembalikan.
  var toastEl = null, toastTimer = null, undoFn = null, toastHeld = false, toastReturn = null;

  function toastBusy() {
    return toastHeld || toastEl.contains(document.activeElement) || toastEl.matches(":hover");
  }
  function armToast() {
    clearTimeout(toastTimer);
    if (!toastEl || toastEl.classList.contains("hidden") || toastBusy()) return;
    toastTimer = setTimeout(function () {
      if (toastBusy()) armToast(); else hideToast(); // masih difokus/disorot: tunggu lagi
    }, undoFn ? 8000 : 2500);
  }

  function hideToast() {
    clearTimeout(toastTimer);
    var had = toastEl && toastEl.contains(document.activeElement);
    if (toastEl) toastEl.classList.add("hidden");
    undoFn = null;
    toastHeld = false;
    if (had) {
      var back = (toastReturn && toastReturn.isConnected && toastReturn) ||
        document.querySelector("#notesList .note-card") || fallbackFocus();
      if (back) back.focus();
    }
    toastReturn = null;
  }

  function toast(msg, opt) {
    opt = opt || {};
    if (!toastEl) {
      toastEl = document.createElement("div");
      toastEl.setAttribute("role", "status");
      toastEl.setAttribute("aria-live", "polite");
      toastEl.className = "hidden fixed bottom-4 right-4 z-50 flex items-center gap-3 bg-slate-800 text-white text-sm px-4 py-2 rounded-md shadow-lg";
      document.body.appendChild(toastEl);
      toastEl.addEventListener("mouseenter", function () { toastHeld = true; clearTimeout(toastTimer); });
      toastEl.addEventListener("mouseleave", function () { toastHeld = toastEl.contains(document.activeElement); armToast(); });
      toastEl.addEventListener("focusin", function (e) {
        if (e.relatedTarget && !toastEl.contains(e.relatedTarget)) toastReturn = e.relatedTarget;
        toastHeld = true;
        clearTimeout(toastTimer);
      });
      toastEl.addEventListener("focusout", function (e) {
        if (toastEl.contains(e.relatedTarget)) return;
        toastHeld = toastEl.matches(":hover");
        armToast();
      });
    }
    toastEl.innerHTML = "<span></span>";
    toastEl.firstChild.textContent = msg;
    undoFn = opt.onAction || null;
    if (undoFn) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "toast-action font-semibold underline underline-offset-2 rounded px-1";
      b.textContent = "Urungkan";
      b.title = "Urungkan (Ctrl+Z)";
      b.setAttribute("aria-keyshortcuts", "Control+Z");
      b.addEventListener("click", function () { var f = undoFn; hideToast(); if (f) f(); });
      toastEl.appendChild(b);
    }
    toastEl.classList.remove("hidden");
    armToast();
  }

  function announce(msg) {
    var el = $("clStatus");
    el.textContent = "";
    setTimeout(function () { el.textContent = msg; }, 30);
  }

  // ---- Aksi catatan ----
  function putNote(id, data) {
    return fetch("/api/notes/" + id, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    }).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    }).then(function (n) {
      tell("changed", id);
      return n;
    }, function () {
      toast("Gagal memperbarui catatan. Coba lagi.");
      return null;
    });
  }

  // Kartu yang difokus setelah kartu ini hilang dari daftar (dihapus/diarsipkan).
  function neighbourCard(id) {
    var el = $("note-" + id);
    var next = el && (el.nextElementSibling || el.previousElementSibling);
    return next ? next.id.replace(/^note-/, "") : null;
  }

  function undoAction(id, reopenSticky) {
    return fetch("/api/notes/" + id + "/undo", { method: "POST" }).then(function (r) {
      if (r.status === 410) throw new Error("Sudah tidak bisa diurungkan.");
      if (!r.ok) { var e = new Error("Gagal mengurungkan."); e.retry = true; throw e; }
      return r.json();
    }).then(function (n) {
      tell("changed", id);
      toast("Dikembalikan");
      pendingFocus = id;
      var a = deskApi();
      if (reopenSticky && desktop && a && !n.archived) {
        return a.sticky_open(id).then(loadNotes, loadNotes);
      }
      return loadNotes();
    }).catch(function (err) {
      if (err.retry) toast(err.message, { onAction: function () { undoAction(id, reopenSticky); } });
      else toast(err.message);
    });
  }

  function toggleDone(note) {
    if (doneBusy[note.id]) return; // klik ganda tidak boleh memajukan tugas berulang dua kali
    doneBusy[note.id] = true;
    var wantDone = !note.done;
    var next = neighbourCard(note.id);
    askDone[note.id] = false;
    // expect_due: tenggat yang terlihat; server tidak memajukan bila sudah dimajukan jendela lain.
    return putNote(note.id, { done: wantDone, expect_due: note.due || null }).then(function (n) {
      doneBusy[note.id] = false;
      if (!n) return;
      if (n.recurred) {
        toast("Selesai. Berikutnya: " + fmtDate(n.due), { onAction: function () { undoAction(n.id, false); } });
      } else if (wantDone && !n.done) {
        // Server tidak memajukan tugas berulang: tenggat sudah diperbarui di jendela lain
        // atau tugas baru saja diselesaikan. Tidak ada yang berubah.
        toast("Sudah diselesaikan sebelumnya. Berikutnya: " + fmtDate(n.due));
      } else {
        toast(wantDone ? "Ditandai selesai" : "Dibuka kembali");
        if (n.done && !archiveView && !$("showDone").checked) pendingFocus = next || "";
      }
      return loadNotes();
    });
  }

  function deleteNote(id) {
    var reopen = !!onDesktop[id];
    var next = neighbourCard(id);
    fetch("/api/notes/" + id, { method: "DELETE" }).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      tell("deleted", id);
      toast("Catatan dihapus", { onAction: function () { undoAction(id, reopen); } });
      pendingFocus = next || "";
      loadNotes();
    }).catch(function () { toast("Gagal menghapus catatan. Coba lagi."); });
  }

  function setArchived(id, archived) {
    var reopen = !!onDesktop[id];
    var next = neighbourCard(id);
    putNote(id, { archived: archived }).then(function (n) {
      if (!n) return;
      if (archived) {
        tell("archived", id);
        toast("Catatan diarsipkan", { onAction: function () { undoAction(id, reopen); } });
      } else {
        toast("Dipulihkan dari arsip");
      }
      pendingFocus = next || "";
      loadNotes();
    });
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
    if (!desktop || archiveView || e.button !== 0 || e.pointerType === "touch") return;
    // Seret dari pegangan atau area kosong kartu; dari teks tetap bisa menyeleksi teks.
    // Checklist punya seret sendiri (urutan item), jadi tidak memulai seret kartu.
    if (e.target.closest("[data-checklist], .cl-ask")) return;
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

  function resetFilters() {
    catFilter = "";
    $("q").value = "";
    $("tagFilter").value = "";
    $("prioFilter").value = "";
    $("showDone").checked = true;
  }

  function focusFromHash() {
    var m = /^#note-([0-9a-f]+)$/.exec(location.hash || "");
    if (!m) return;
    history.replaceState(null, "", location.pathname);
    var el = document.getElementById("note-" + m[1]);
    var inArchive = allArchived.some(function (n) { return n.id === m[1]; });
    if (!el && (inArchive || allNotes.some(function (n) { return n.id === m[1]; }))) {
      // Kartunya tersaring atau ada di arsip: tampilkan semua dulu.
      archiveView = inArchive;
      resetFilters();
      populateTags();
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

  // Muat ulang karena perubahan dari jendela lain; ditunda selama checklist sedang diketik.
  var reloadTimer = null;
  function reloadSoon() {
    clearTimeout(reloadTimer);
    reloadTimer = setTimeout(function () {
      if (ctl && ctl.isBusy()) { deferredReload = true; return; }
      loadNotes();
    }, 250);
  }

  function onListClick(e) {
    if (e.target.closest("[data-retry]")) { loadNotes(); return; }
    var btn = e.target.closest("button[data-action]");
    if (!btn) return;
    var id = btn.getAttribute("data-id");
    var action = btn.getAttribute("data-action");
    var note = findNote(id);
    if (!note) return;
    if (action === "done") toggleDone(note);
    else if (action === "pin") putNote(id, { pinned: !note.pinned }).then(loadNotes);
    else if (action === "sticky") toggleSticky(id);
    else if (action === "edit") startEdit(note);
    else if (action === "archive") setArchived(id, true);
    else if (action === "unarchive") setArchived(id, false);
    else if (action === "del") deleteNote(id);
    else if (action === "checklist") {
      addOpen[id] = true;
      renderCard(id);
      var input = document.querySelector('#note-' + id + ' [data-cl="new"]');
      if (input) input.focus();
    }
    else if (action === "ask-yes") {
      if (!note.done && DailyChecklist.allDone(note)) toggleDone(note); else dismissAsk(id);
    }
    else if (action === "ask-no") dismissAsk(id);
    else if (action === "toggle") {
      expanded[id] = !expanded[id];
      renderCard(id);
    }
  }

  function dismissAsk(id) {
    askDone[id] = false;
    renderCard(id);
    var btn = document.querySelector('#note-' + id + ' [data-action="done"]');
    if (btn) btn.focus();
  }

  function onCatClick(e) {
    var btn = e.target.closest("button[data-cat]");
    if (!btn) return;
    catFilter = btn.getAttribute("data-cat");
    renderCatFilter();
    render();
  }

  function toggleArchiveView() {
    archiveView = !archiveView;
    catFilter = "";
    populateTags();
    renderCatFilter();
    render();
  }

  function isTextField(el) {
    if (!el) return false;
    var t = el.tagName;
    return (t === "INPUT" && /^(text|search|number|date)$/.test(el.type)) || t === "TEXTAREA" || el.isContentEditable;
  }

  document.addEventListener("DOMContentLoaded", function () {
    ctl = new DailyChecklist.Controller($("notesList"), {
      icon: DailyIcon,
      getNote: findNote,
      onChange: function (n, focus, quiet) {
        var old = findNote(n.id);
        setNote(n);
        tell("changed", n.id);
        if (!quiet) { renderCard(n.id); return; }
        // Perubahan senyap (teks tersimpan): kartu tidak digambar ulang, hanya chip progres.
        if (old && old.checklist_total === n.checklist_total && old.checklist_done === n.checklist_done) return;
        var cp = $("cp-" + n.id);
        if (cp) cp.outerHTML = progChipHtml(n);
      },
      reveal: function (id) {
        if (clOpen[id]) return;
        clOpen[id] = true;
        renderCard(id);
      },
      onAllDone: function (n) {
        askDone[n.id] = true;
        renderCard(n.id);
        announce("Semua item selesai. Tandai catatan selesai?");
      },
      onMore: function (id) {
        clOpen[id] = !clOpen[id];
        renderCard(id);
        var more = document.querySelector('#note-' + id + ' [data-cl="more"]');
        if (more) more.focus();
      },
      announce: announce,
      onError: function (msg) { toast(msg); loadNotes(); },
      onMissing: function () { loadNotes(); }
    });

    $("noteForm").addEventListener("submit", submitForm);
    $("btnNew").addEventListener("click", newNote);
    $("btnCancel").addEventListener("click", closeForm);
    $("btnClose").addEventListener("click", closeForm);
    $("btnArchive").addEventListener("click", toggleArchiveView);
    $("notesList").addEventListener("click", onListClick);
    $("catFilter").addEventListener("click", onCatClick);
    $("q").addEventListener("input", render);
    $("tagFilter").addEventListener("change", render);
    $("prioFilter").addEventListener("change", render);
    $("showDone").addEventListener("change", render);
    // Tugas berulang wajib bertenggat: isi hari ini bila masih kosong (terlihat oleh pengguna).
    $("f-recur").addEventListener("change", function () {
      if ($("f-recur").value && !$("f-due").value) $("f-due").value = todayIso();
    });
    $("notesList").addEventListener("pointerdown", onCardPointerDown);
    document.addEventListener("pointermove", onPointerMove);
    document.addEventListener("pointerup", function (e) { if (drag && e.pointerId === drag.pid) endDrag(); });
    document.addEventListener("pointercancel", endDrag);
    window.addEventListener("blur", endDrag);
    // Fase capture: Esc membatalkan seret kartu / menutup tawaran "tandai selesai" tanpa
    // diteruskan ke Esc → Beranda.
    window.addEventListener("keydown", function (e) {
      if (e.key !== "Escape") return;
      if (drag) { endDrag(); e.preventDefault(); e.stopPropagation(); return; }
      var ask = document.activeElement && document.activeElement.closest && document.activeElement.closest(".cl-ask");
      if (ask) {
        var id = ask.querySelector("[data-id]").getAttribute("data-id");
        e.preventDefault(); e.stopPropagation();
        dismissAsk(id);
      }
    }, true);
    // Ctrl+Z = Urungkan selama toast-nya tampil (bukan saat sedang mengetik).
    document.addEventListener("keydown", function (e) {
      if (!undoFn || !(e.ctrlKey || e.metaKey) || e.shiftKey || (e.key || "").toLowerCase() !== "z") return;
      if (isTextField(document.activeElement)) return;
      e.preventDefault();
      var f = undoFn;
      hideToast();
      f();
    });
    // Cadangan bila WebView2 tidak meneruskan gerakan di luar jendela: keluar = sobek.
    document.documentElement.addEventListener("mouseleave", function () { if (drag && drag.active) tearOff(); });
    window.addEventListener("hashchange", focusFromHash);
    if (chan) chan.onmessage = function (ev) {
      var m = ev.data || {};
      if (m.type === "changed" || m.type === "sticky" || m.type === "deleted" || m.type === "archived") reloadSoon();
    };
    // Teks checklist yang masih menunggu jeda simpan (dan isi "Tambah item") dikirim saat halaman
    // dimuat ulang/ditutup. fetch keepalive tetap terkirim setelah halaman hilang.
    window.addEventListener("pagehide", function () {
      var ids = Object.keys(ctl.texts).concat(Object.keys(ctl.drafts));
      ids.filter(function (id, i) { return ids.indexOf(id) === i; }).forEach(function (id) {
        var ops = ctl.takePending(id).concat(ctl.takeDraft(id));
        var nw = document.querySelector('[data-checklist="' + id + '"] [data-cl="new"]');
        if (nw) nw.value = ""; // sudah dikirim: jangan terkirim dua kali bila halaman dipulihkan
        if (ops.length) fetch("/api/notes/" + id + "/checklist", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ops: ops }),
          keepalive: true
        });
      });
    });
    // Dipulihkan dari back-forward cache (tombol Kembali): tampilan dari sebelum pagehide, muat ulang.
    window.addEventListener("pageshow", function (e) { if (e.persisted) loadNotes(); });
    // Muat ulang yang tertunda dijalankan begitu checklist tidak lagi diketik.
    setInterval(function () {
      if (deferredReload && ctl && !ctl.isBusy()) loadNotes();
    }, 1500);
    detectDesktop();
    // API desktop bisa siap setelah muatan pertama: muat ulang agar penanda "Di desktop" terisi.
    window.addEventListener("pywebviewready", function () {
      detectDesktop();
      if (desktop && loaded) loadNotes(); else render();
    });
    loadNotes();
  });
})();
