// Catatan & Pengingat — CRUD + render + filter kategori (vanilla JS).
(function () {
  "use strict";

  var allNotes = [];
  var editingId = null;
  var catFilter = ""; // "" = semua kategori

  var CATS = window.CATEGORIES || [];
  var CAT_BY_ID = {};
  CATS.forEach(function (c) { CAT_BY_ID[c.id] = c; });
  var DEFAULT_CAT = (CATS[0] && CATS[0].id) || "umum";

  // Peta warna kategori -> kelas Tailwind (string literal agar pasti ter-generate).
  var CAT_CHIP = {
    slate: "bg-slate-100 text-slate-700",
    green: "bg-green-100 text-green-700",
    blue: "bg-blue-100 text-blue-700",
    purple: "bg-purple-100 text-purple-700",
    amber: "bg-amber-100 text-amber-700",
    pink: "bg-pink-100 text-pink-700"
  };

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
    done:      { border: "",                              badge: "bg-slate-100 text-slate-500" }
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
    return CAT_BY_ID[id] || CAT_BY_ID[DEFAULT_CAT] || { label: "Umum", emoji: "🗒️", color: "slate" };
  }
  function chipCls(color) { return CAT_CHIP[color] || CAT_CHIP.slate; }
  function noteCat(n) { return CAT_BY_ID[n.category] ? n.category : DEFAULT_CAT; }

  function cardHtml(n) {
    var meta = STATUS[n.status] || STATUS.none;
    var cat = catMeta(n.category);
    var titleCls = n.done ? "line-through text-slate-400" : "text-slate-900";
    var catChip = '<span class="inline-flex items-center gap-1 text-[11px] font-medium rounded px-1.5 py-0.5 ' + chipCls(cat.color) + '">' + cat.emoji + " " + esc(cat.label) + "</span>";
    var due = dueLabel(n);
    var dueChip = due
      ? '<span class="text-xs font-medium rounded-full px-2 py-0.5 ' + (meta.badge || "bg-slate-100 text-slate-600") + '">' + esc(due) + "</span>"
      : "";
    var tags = (n.tags || []).map(function (t) {
      return '<span class="inline-block text-[11px] bg-slate-100 text-slate-600 rounded px-1.5 py-0.5">#' + esc(t) + "</span>";
    }).join(" ");
    var body = n.body ? '<p class="text-sm text-slate-600 mt-1 whitespace-pre-wrap">' + esc(n.body) + "</p>" : "";
    var pin = n.pinned ? '<span title="Disematkan">📌</span> ' : "";
    return '' +
      '<div class="bg-white rounded-lg border border-slate-200 ' + meta.border + ' p-4 ' + (n.done ? "opacity-70" : "") + '">' +
        '<div class="flex items-start justify-between gap-3">' +
          '<div class="min-w-0">' +
            '<h3 class="font-semibold ' + titleCls + ' break-words">' + pin + esc(n.title || "(tanpa judul)") + "</h3>" +
            body +
            '<div class="flex flex-wrap items-center gap-2 mt-2">' + catChip + " " + dueChip + " " + tags + "</div>" +
          "</div>" +
          '<div class="flex flex-col items-end gap-1 shrink-0">' +
            '<button data-action="done" data-id="' + n.id + '" class="text-xs px-2 py-1 rounded border border-slate-300 hover:bg-slate-50">' + (n.done ? "↩︎ Batalkan" : "✓ Selesai") + "</button>" +
            '<div class="flex gap-1">' +
              '<button data-action="pin" data-id="' + n.id + '" title="Sematkan" class="text-xs px-2 py-1 rounded border border-slate-300 hover:bg-slate-50">' + (n.pinned ? "Lepas" : "📌") + "</button>" +
              '<button data-action="edit" data-id="' + n.id + '" title="Edit" class="text-xs px-2 py-1 rounded border border-slate-300 hover:bg-slate-50">✏️</button>' +
              '<button data-action="del" data-id="' + n.id + '" title="Hapus" class="text-xs px-2 py-1 rounded border border-red-200 text-red-600 hover:bg-red-50">🗑️</button>' +
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

  function chipBtn(id, label, emoji, count, active) {
    var cls = active
      ? "bg-blue-600 text-white border-blue-600"
      : "bg-white text-slate-600 border-slate-300 hover:bg-slate-50";
    return '<button type="button" data-cat="' + id + '" class="text-sm px-3 py-1 rounded-full border ' + cls + '">' +
      (emoji ? emoji + " " : "") + esc(label) + ' <span class="opacity-70">(' + count + ")</span></button>";
  }

  function renderCatFilter() {
    var el = $("catFilter");
    if (!el) return;
    var counts = {};
    allNotes.forEach(function (n) { var id = noteCat(n); counts[id] = (counts[id] || 0) + 1; });
    var html = chipBtn("", "Semua", "", allNotes.length, catFilter === "");
    CATS.forEach(function (c) {
      html += chipBtn(c.id, c.label, c.emoji, counts[c.id] || 0, catFilter === c.id);
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
    $("emptyState").classList.toggle("hidden", list.length > 0);
  }

  function loadNotes() {
    return fetch("/api/notes").then(function (r) { return r.json(); }).then(function (data) {
      allNotes = data.notes || [];
      updateCounts(data.counts);
      populateTags();
      renderCatFilter();
      render();
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
    var url = wasEdit ? "/api/notes/" + editingId : "/api/notes";
    fetch(url, {
      method: wasEdit ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).then(function (r) {
      if (!r.ok) throw new Error("Gagal menyimpan");
      return r.json();
    }).then(function () {
      closeForm();
      toast(wasEdit ? "Catatan diperbarui" : "Catatan disimpan");
      loadNotes();
    }).catch(function (err) { $("formMsg").textContent = err.message; });
  }

  function patch(id, data, msg) {
    return fetch("/api/notes/" + id, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    }).then(function () { if (msg) toast(msg); return loadNotes(); });
  }

  function onListClick(e) {
    var btn = e.target.closest("button[data-action]");
    if (!btn) return;
    var id = btn.getAttribute("data-id");
    var action = btn.getAttribute("data-action");
    var note = allNotes.filter(function (n) { return n.id === id; })[0];
    if (!note) return;
    if (action === "done") patch(id, { done: !note.done }, note.done ? "Dibuka kembali" : "Ditandai selesai");
    else if (action === "pin") patch(id, { pinned: !note.pinned });
    else if (action === "edit") startEdit(note);
    else if (action === "del") {
      if (confirm("Hapus catatan ini?")) {
        fetch("/api/notes/" + id, { method: "DELETE" }).then(function () { toast("Catatan dihapus"); loadNotes(); });
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
    loadNotes();
  });
})();
