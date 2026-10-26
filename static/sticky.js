// Sticky note di desktop: edit langsung, simpan otomatis, sinkron dengan halaman Catatan.
(function () {
  "use strict";

  var S = window.STICKY || {};
  var ID = S.id;
  var $ = function (id) { return document.getElementById(id); };
  var note = null;
  var dirty = false;
  var saveTimer = null;
  var savedTimer = null;
  var undoTimer = null;
  var undoMsgTimer = null;
  var addOpen = false;   // kolom "Tambah item" dibuka walau checklist masih kosong
  var listStale = false; // daftar belum digambar ulang karena sedang diketik
  var doneBusy = false;  // permintaan Selesai masih berjalan (cegah klik ganda)
  var saving = null;     // simpan judul/isi yang masih berjalan
  var ctl = null;
  var chan = "BroadcastChannel" in window ? new BroadcastChannel("dailyapp-notes") : null;

  var COLORS = {};
  (S.colors || []).forEach(function (c) { COLORS[c.id] = c; });
  var CATS = {};
  (S.categories || []).forEach(function (c) { CATS[c.id] = c; });
  var PRIO_LABEL = {};
  (S.priorities || []).forEach(function (p) { PRIO_LABEL[p.id] = p.label; });
  var RECUR_LABEL = {};
  (S.recurrences || []).forEach(function (r) { RECUR_LABEL[r.id] = r.label; });

  // pywebview mengisi api dalam dua langkah ({} dulu, fungsi menyusul): belum lengkap = belum siap.
  function api() {
    var p = window.pywebview;
    return p && p.api && typeof p.api.sticky_close === "function" ? p.api : null;
  }
  function tell(type) { if (chan) chan.postMessage({ type: type, id: ID }); }
  function icon(name) {
    return '<svg class="ico" aria-hidden="true" focusable="false"><use href="/static/vendor/tabler-sprite.svg#' + name + '"></use></svg>';
  }
  function esc(s) {
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function applyColor(id) {
    var c = COLORS[id] || COLORS.krem || { bg: "#fbf1cf", ink: "#2b2410", muted: "#5f5023", focus: "#0070d1" };
    var root = document.documentElement.style;
    root.setProperty("--bg", c.bg);
    root.setProperty("--ink", c.ink);
    root.setProperty("--muted", c.muted);
    root.setProperty("--focus", c.focus || "#0070d1");
    Array.prototype.forEach.call(document.querySelectorAll(".sw"), function (b) {
      b.setAttribute("aria-pressed", String(b.getAttribute("data-color") === id));
    });
  }

  function setOnTop(on) {
    var b = $("btnTop");
    b.setAttribute("aria-pressed", String(!!on));
    b.title = on ? "Selalu di atas (aktif)" : "Selalu di atas";
  }

  function shortDate(due) {
    var p = String(due).split("T")[0].split("-");
    return p[2] + "/" + p[1];
  }

  function dueText(n) {
    if (!n.due) return "";
    var p = String(n.due).split("T")[0].split("-");
    var due = new Date(+p[0], +p[1] - 1, +p[2]);
    var t = new Date();
    var diff = Math.round((due - new Date(t.getFullYear(), t.getMonth(), t.getDate())) / 86400000);
    if (n.done) return "Tenggat " + p[2] + "/" + p[1];
    if (diff < 0) return "Lewat " + (-diff) + " hari";
    if (diff === 0) return "Jatuh tempo hari ini";
    return diff + " hari lagi";
  }

  // Sedang diketik di jendela ini? (activeElement tetap menunjuk kolom terakhir walau
  // jendelanya tidak aktif, jadi cek juga document.hasFocus()).
  function editing(el) { return document.hasFocus() && document.activeElement === el; }

  // Isi catatan menyesuaikan tinggi teksnya bila ada checklist (seluruh badan sticky yang bergulir).
  function autosize() {
    var t = $("text"), b = $("body");
    if (b.classList.contains("has-list")) {
      var top = b.scrollTop; // height:auto memendekkan isi dan Chromium mengembalikan gulir ke 0
      t.style.height = "auto";
      t.style.height = Math.max(t.scrollHeight, 40) + "px";
      b.scrollTop = top;
    } else {
      t.style.height = "";
    }
  }

  function renderList() {
    if (!note) return;
    listStale = false;
    var has = (note.checklist || []).length > 0;
    var draft = ctl ? ctl.drafts[ID] : "";
    $("cl").innerHTML = DailyChecklist.html(note, { icon: icon, addOpen: addOpen, draft: draft });
    if (ctl) ctl.restoreInputs(ID);
    $("body").classList.toggle("has-list", has || addOpen || !!draft);
    $("btnList").hidden = has || addOpen || !!draft;
    autosize();
  }

  function renderMeta(n) {
    var cat = CATS[n.category] || { label: "Catatan", icon: "notes" };
    $("cat").innerHTML = icon(cat.icon || "notes") + '<span id="catLabel"></span>';
    $("catLabel").textContent = cat.label;
    document.body.classList.toggle("is-done", !!n.done);
    $("btnDone").innerHTML = icon(n.done ? "arrow-back-up" : "check") + "<span>" + (n.done ? "Batalkan" : "Selesai") + "</span>";
    var due = $("due");
    var text = dueText(n);
    due.hidden = !text;
    due.innerHTML = (n.recurrence ? icon("repeat") + " " : "") + esc(text) +
      (n.recurrence ? '<span class="sr-only">, berulang ' + esc((RECUR_LABEL[n.recurrence] || "").toLowerCase()) + "</span>" : "");
    due.title = n.recurrence ? "Berulang " + (RECUR_LABEL[n.recurrence] || "").toLowerCase() : "";
    due.className = "due " + (n.status || "");
    var prio = $("prio");
    prio.hidden = !n.priority;
    if (n.priority) {
      var label = PRIO_LABEL[n.priority] || "";
      prio.className = "prio " + n.priority;
      prio.title = "Prioritas " + label.toLowerCase();
      prio.innerHTML = icon("flag") + '<span class="lbl" aria-hidden="true">' + esc(label) + '</span><span class="ab" aria-hidden="true">' +
        esc(label.charAt(0)) + '</span><span class="sr-only">Prioritas ' + esc(label.toLowerCase()) + "</span>";
    }
    if (n.done || !DailyChecklist.allDone(n)) hideAsk();
    document.title = (n.title || "Catatan") + " · Daily App";
  }

  function render(n) {
    note = n;
    if (n.archived) { closeSelf(); return; }
    if (!dirty) {
      if (!editing($("title"))) $("title").value = n.title || "";
      if (!editing($("text"))) $("text").value = n.body || "";
    }
    renderMeta(n);
    // Daftar tidak digambar ulang selama item sedang diketik/diseret; menyusul setelahnya.
    if (ctl && ctl.isBusy()) { listStale = true; autosize(); }
    else renderList();
  }

  var closing = false;
  function closeSelf() {
    if (closing) return; // pesan "deleted" dan respons 404 bisa datang bersamaan
    var a = api();
    if (!a) {
      // window.close() tidak berfungsi di WebView2: tunggu jembatan pywebview siap.
      window.addEventListener("pywebviewready", closeSelf, { once: true });
      return;
    }
    closing = true;
    try {
      a.sticky_close(ID).then(null, function () { closing = false; }); // gagal: boleh dicoba lagi
    } catch (_) {
      closing = false;
    }
  }

  function load() {
    return fetch("/api/notes/" + ID).then(function (r) {
      if (r.status === 404) { closeSelf(); throw new Error("hilang"); }
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    }).then(render).catch(function () {});
  }

  function showError(msg) {
    clearTimeout(savedTimer);
    var s = $("saved");
    s.textContent = msg;
    s.classList.add("wrap");
  }

  function flashSaved(msg) {
    $("saved").classList.remove("wrap");
    $("saved").textContent = msg;
    clearTimeout(savedTimer);
    savedTimer = setTimeout(function () { $("saved").textContent = ""; }, 1800);
  }

  function put(data) {
    return fetch("/api/notes/" + ID, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
      keepalive: true // tetap terkirim walau jendela sticky sedang ditutup
    }).then(function (r) {
      if (r.status === 404) { closeSelf(); throw new Error("hilang"); }
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    });
  }

  // Hasil: true bila tersimpan atau memang tidak ada perubahan.
  function save() {
    clearTimeout(saveTimer);
    // Simpan yang masih berjalan (mis. dari blur sesaat sebelum klik X) ditunggu hasilnya.
    if (!dirty) return saving || Promise.resolve(true);
    if (!note) return Promise.resolve(false); // catatan belum termuat: jangan timpa dengan isian kosong
    dirty = false;
    var p = put({ title: $("title").value, body: $("text").value }).then(function (n) {
      note = n;
      flashSaved("Tersimpan");
      tell("changed");
      return true;
    }).catch(function () {
      dirty = true;
      showError("Gagal menyimpan");
      return false;
    });
    saving = p;
    p.then(function () { if (saving === p) saving = null; });
    return p;
  }

  // Judul/isi, teks checklist, dan isi "Tambah item" yang belum terkirim, sekaligus.
  // Hasil: true bila semuanya tersimpan.
  function saveAll() {
    var list = ctl ? ctl.commit(ID) : Promise.resolve(true);
    return Promise.all([save(), list]).then(function (r) { return r[0] && r[1] !== false; });
  }

  function syncSend(method, url, data) {
    var xhr = new XMLHttpRequest();
    xhr.open(method, url, false);
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.send(JSON.stringify(data));
    return xhr.status >= 200 && xhr.status < 300;
  }

  // Simpan seketika (XHR sinkron) sebelum jendela ditutup dari luar: Alt+F4, atau
  // "Keluar" di tray (dipanggil lewat evaluate_js oleh app/desktop_shell.py).
  window.stickyFlushSync = function () {
    clearTimeout(saveTimer);
    var ok = true;
    try {
      var ops = ctl ? ctl.takePending(ID).concat(ctl.takeDraft(ID)) : [];
      if (ops.length && syncSend("POST", "/api/notes/" + ID + "/checklist", { ops: ops })) tell("changed");
      if (dirty && note) {
        if (syncSend("PUT", "/api/notes/" + ID, { title: $("title").value, body: $("text").value })) { dirty = false; tell("changed"); }
        else ok = false;
      }
    } catch (_) { ok = !dirty; /* tetap lanjut menutup */ }
    return ok;
  };

  function onInput() {
    dirty = true;
    $("saved").textContent = "";
    $("saved").classList.remove("wrap");
    clearTimeout(saveTimer);
    saveTimer = setTimeout(save, 600);
  }

  function showAsk() {
    $("ask").hidden = false;
    flashSaved("Semua item selesai");
  }
  function hideAsk() {
    var ask = $("ask");
    if (!ask.hidden && ask.contains(document.activeElement)) $("btnDone").focus();
    ask.hidden = true;
  }

  // Bilah Urungkan: hilang setelah 8 detik, kecuali sedang difokus atau disorot.
  function armUndo() {
    clearTimeout(undoTimer);
    var bar = $("undoBar");
    var held = function () { return bar.contains(document.activeElement) || bar.matches(":hover"); };
    if (bar.hidden || held()) return;
    undoTimer = setTimeout(function () { if (held()) armUndo(); else hideUndo(); }, 8000);
  }
  function showUndo(msg) {
    var m = $("undoMsg");
    clearTimeout(undoMsgTimer);
    m.textContent = "";
    $("undoBar").hidden = false;
    // Ditulis setelah wilayah live tampil (dan dikosongkan dulu) agar selalu diumumkan.
    undoMsgTimer = setTimeout(function () { m.textContent = msg; }, 50);
    armUndo();
  }
  function hideUndo() {
    clearTimeout(undoTimer);
    clearTimeout(undoMsgTimer);
    var bar = $("undoBar");
    if (bar.contains(document.activeElement)) $("btnDone").focus();
    bar.hidden = true;
  }

  function toggleDone() {
    if (!note || doneBusy) return; // klik ganda tidak boleh memajukan tugas berulang dua kali
    doneBusy = true;
    // Nilai saat diklik (sebelum simpan async) agar server bisa menolak tampilan basi.
    var want = !note.done, expect = note.due || null;
    hideAsk();
    saveAll().then(function () { return put({ done: want, expect_due: expect }); }).then(function (n) {
      render(n);
      tell("changed");
      if (n.recurred) showUndo("Berikutnya " + shortDate(n.due));
    }).catch(function () { showError("Gagal menyimpan"); })
      .then(function () { doneBusy = false; });
  }

  // Ubah ukuran lewat pegangan pojok (pointer capture, dibatasi per frame).
  function setupGrip() {
    var grip = $("grip");
    var start = null;
    var pending = null;
    function flush() {
      var a = api();
      if (pending && a) a.sticky_resize(ID, pending.w, pending.h);
      pending = null;
    }
    grip.addEventListener("pointerdown", function (e) {
      if (e.button !== 0) return;
      e.preventDefault();
      start = { x: e.screenX, y: e.screenY, w: window.innerWidth, h: window.innerHeight };
      grip.setPointerCapture(e.pointerId);
    });
    grip.addEventListener("pointermove", function (e) {
      if (!start) return;
      if (!(e.buttons & 1)) { end(e); return; } // tombol sudah dilepas di luar jendela
      var first = !pending;
      pending = { w: start.w + (e.screenX - start.x), h: start.h + (e.screenY - start.y) };
      if (first) requestAnimationFrame(flush);
    });
    function end(e) {
      if (!start) return;
      start = null;
      try { grip.releasePointerCapture(e.pointerId); } catch (_) {}
    }
    grip.addEventListener("pointerup", end);
    grip.addEventListener("pointercancel", end);
    grip.addEventListener("lostpointercapture", function () { start = null; });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var st = S.sticky || {};
    applyColor(st.color);
    setOnTop(st.on_top);

    ctl = new DailyChecklist.Controller($("body"), {
      icon: icon,
      getNote: function () { return note; },
      onChange: function (n, focus, quiet) {
        note = n;
        tell("changed");
        if (n.done || !DailyChecklist.allDone(n)) hideAsk();
        if (quiet) return;
        renderMeta(n);
        renderList();
      },
      onAllDone: showAsk,
      announce: flashSaved,
      onError: function (msg) { showError(msg); load(); },
      onMissing: closeSelf,
      scroller: $("body")
    });

    // Tombol di bilah seret: cegah mousedown memulai seret jendela.
    Array.prototype.forEach.call(document.querySelectorAll(".bar button"), function (b) {
      b.addEventListener("mousedown", function (e) { e.stopPropagation(); });
    });

    $("title").addEventListener("input", onInput);
    $("text").addEventListener("input", function () { onInput(); autosize(); });
    $("title").addEventListener("blur", save);
    $("text").addEventListener("blur", save);
    $("title").addEventListener("keydown", function (e) {
      if (e.key !== "Enter") return;
      e.preventDefault();
      var first = document.querySelector('#cl [data-cl="text"]');
      (first || $("text")).focus();
    });
    // Daftar yang tertunda digambar ulang begitu fokus keluar dari checklist.
    $("cl").addEventListener("focusout", function () {
      setTimeout(function () { if (listStale && !ctl.isBusy()) renderList(); }, 60);
    });

    $("btnList").addEventListener("click", function () {
      addOpen = true;
      renderList();
      var input = document.querySelector('#cl [data-cl="new"]');
      if (input) input.focus();
    });

    $("btnDone").addEventListener("click", toggleDone);
    $("askYes").addEventListener("click", toggleDone);
    $("askNo").addEventListener("click", hideAsk);
    $("btnUndo").addEventListener("click", function () {
      hideUndo();
      fetch("/api/notes/" + ID + "/undo", { method: "POST" }).then(function (r) {
        if (r.status === 410) throw new Error("Sudah tidak bisa diurungkan");
        if (!r.ok) { var e = new Error("Gagal mengurungkan"); e.retry = true; throw e; }
        return r.json();
      }).then(function (n) {
        render(n);
        tell("changed");
        flashSaved("Dikembalikan");
      }).catch(function (err) {
        if (err.retry) showUndo(err.message + ". Coba lagi?"); // urungkan masih tersimpan di server
        else showError(err.message);
      });
    });
    ["focusin", "mouseenter"].forEach(function (t) { $("undoBar").addEventListener(t, function () { clearTimeout(undoTimer); }); });
    $("undoBar").addEventListener("mouseleave", armUndo);
    $("undoBar").addEventListener("focusout", function () { setTimeout(armUndo, 0); });

    $("btnTop").addEventListener("click", function () {
      var on = $("btnTop").getAttribute("aria-pressed") !== "true";
      var a = api();
      if (!a) return;
      a.sticky_set_on_top(ID, on).then(setOnTop);
    });

    $("btnColor").addEventListener("click", function () {
      var p = $("palette");
      p.hidden = !p.hidden;
      $("btnColor").setAttribute("aria-expanded", String(!p.hidden));
      if (!p.hidden) {
        var cur = p.querySelector('[aria-pressed="true"]') || p.querySelector(".sw");
        if (cur) cur.focus();
      }
    });
    $("palette").addEventListener("click", function (e) {
      var b = e.target.closest(".sw");
      if (!b) return;
      var color = b.getAttribute("data-color");
      applyColor(color);
      fetch("/api/stickies/" + ID, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ color: color })
      });
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "F4" && e.altKey) window.stickyFlushSync(); // Alt+F4 menutup jendela
      if (e.key !== "Escape") return;
      if (!$("palette").hidden) {
        $("palette").hidden = true;
        $("btnColor").setAttribute("aria-expanded", "false");
        $("btnColor").focus();
      } else if (!$("ask").hidden) {
        hideAsk();
      }
    });

    $("btnApp").addEventListener("click", function () {
      var a = api();
      saveAll().then(function () { if (a) a.show_main("/notes#note-" + ID); });
    });

    $("btnClose").addEventListener("click", function () {
      saveAll().then(function (ok) {
        if (!ok) return; // gagal simpan: biarkan terbuka agar isian tidak hilang
        tell("sticky");
        closeSelf();
      });
    });

    if (chan) {
      chan.onmessage = function (ev) {
        var m = ev.data || {};
        if (m.id !== ID) return;
        if (m.type === "deleted" || m.type === "archived") closeSelf();
        else if (m.type === "changed" && !dirty) load();
      };
    }

    // Ditutup dengan cara apa pun (mis. Alt+F4): beri tahu halaman Catatan agar penandanya diperbarui.
    window.addEventListener("pagehide", function () {
      if (dirty) save(); // fetch keepalive tetap terkirim setelah halaman ditutup
      if (ctl) ctl.commit(ID);
      tell("sticky");
    });

    setupGrip();
    var rzFrame = 0;
    window.addEventListener("resize", function () {
      if (rzFrame) return;
      rzFrame = requestAnimationFrame(function () { rzFrame = 0; autosize(); });
    });
    load();
    // Status jatuh tempo bisa berubah karena waktu berjalan (mis. lewat tengah malam).
    setInterval(function () { if (!dirty) load(); }, 60000);
  });
})();
