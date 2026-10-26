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
  var chan = "BroadcastChannel" in window ? new BroadcastChannel("dailyapp-notes") : null;

  var COLORS = {};
  (S.colors || []).forEach(function (c) { COLORS[c.id] = c; });
  var CATS = {};
  (S.categories || []).forEach(function (c) { CATS[c.id] = c; });

  function api() { return window.pywebview && window.pywebview.api; }
  function tell(type) { if (chan) chan.postMessage({ type: type, id: ID }); }
  function icon(name) {
    return '<svg class="ico" aria-hidden="true" focusable="false"><use href="/static/vendor/tabler-sprite.svg#' + name + '"></use></svg>';
  }

  function applyColor(id) {
    var c = COLORS[id] || COLORS.krem || { bg: "#fbf1cf", ink: "#2b2410", muted: "#5f5023" };
    var root = document.documentElement.style;
    root.setProperty("--bg", c.bg);
    root.setProperty("--ink", c.ink);
    root.setProperty("--muted", c.muted);
    Array.prototype.forEach.call(document.querySelectorAll(".sw"), function (b) {
      b.setAttribute("aria-pressed", String(b.getAttribute("data-color") === id));
    });
  }

  function setOnTop(on) {
    var b = $("btnTop");
    b.setAttribute("aria-pressed", String(!!on));
    b.title = on ? "Selalu di atas (aktif)" : "Selalu di atas";
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

  function render(n) {
    note = n;
    if (!dirty) {
      if (!editing($("title"))) $("title").value = n.title || "";
      if (!editing($("text"))) $("text").value = n.body || "";
    }
    var cat = CATS[n.category] || { label: "Catatan", icon: "notes" };
    $("cat").innerHTML = icon(cat.icon || "notes") + '<span id="catLabel"></span>';
    $("catLabel").textContent = cat.label;
    document.body.classList.toggle("is-done", !!n.done);
    $("btnDone").innerHTML = icon(n.done ? "arrow-back-up" : "check") + "<span>" + (n.done ? "Batalkan" : "Selesai") + "</span>";
    var due = $("due");
    var text = dueText(n);
    due.hidden = !text;
    due.textContent = text;
    due.className = "due " + (n.status || "");
    document.title = (n.title || "Catatan") + " · Daily App";
  }

  function closeSelf() {
    var a = api();
    if (a) a.sticky_close(ID); else window.close();
  }

  function load() {
    return fetch("/api/notes/" + ID).then(function (r) {
      if (r.status === 404) { closeSelf(); throw new Error("hilang"); }
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    }).then(render).catch(function () {});
  }

  function flashSaved(msg) {
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
    if (!dirty) return Promise.resolve(true);
    if (!note) return Promise.resolve(false); // catatan belum termuat: jangan timpa dengan isian kosong
    dirty = false;
    return put({ title: $("title").value, body: $("text").value }).then(function (n) {
      note = n;
      flashSaved("Tersimpan");
      tell("changed");
      return true;
    }).catch(function () {
      dirty = true;
      $("saved").textContent = "Gagal menyimpan";
      return false;
    });
  }

  // Simpan seketika (XHR sinkron) sebelum jendela ditutup dari luar: Alt+F4, atau
  // "Keluar" di tray (dipanggil lewat evaluate_js oleh app/desktop_shell.py).
  window.stickyFlushSync = function () {
    clearTimeout(saveTimer);
    if (!dirty || !note) return true;
    try {
      var xhr = new XMLHttpRequest();
      xhr.open("PUT", "/api/notes/" + ID, false);
      xhr.setRequestHeader("Content-Type", "application/json");
      xhr.send(JSON.stringify({ title: $("title").value, body: $("text").value }));
      if (xhr.status >= 200 && xhr.status < 300) { dirty = false; tell("changed"); }
    } catch (_) { /* tetap lanjut menutup */ }
    return !dirty;
  };

  function onInput() {
    dirty = true;
    $("saved").textContent = "";
    clearTimeout(saveTimer);
    saveTimer = setTimeout(save, 600);
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

    // Tombol di bilah seret: cegah mousedown memulai seret jendela.
    Array.prototype.forEach.call(document.querySelectorAll(".bar button"), function (b) {
      b.addEventListener("mousedown", function (e) { e.stopPropagation(); });
    });

    $("title").addEventListener("input", onInput);
    $("text").addEventListener("input", onInput);
    $("title").addEventListener("blur", save);
    $("text").addEventListener("blur", save);
    $("title").addEventListener("keydown", function (e) {
      if (e.key === "Enter") { e.preventDefault(); $("text").focus(); }
    });

    $("btnDone").addEventListener("click", function () {
      if (!note) return;
      save().then(function () { return put({ done: !note.done }); }).then(function (n) {
        render(n);
        tell("changed");
      }).catch(function () { $("saved").textContent = "Gagal menyimpan"; });
    });

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
      if (e.key === "Escape" && !$("palette").hidden) {
        $("palette").hidden = true;
        $("btnColor").setAttribute("aria-expanded", "false");
        $("btnColor").focus();
      }
    });

    $("btnApp").addEventListener("click", function () {
      var a = api();
      save().then(function () { if (a) a.show_main("/notes#note-" + ID); });
    });

    $("btnClose").addEventListener("click", function () {
      save().then(function (ok) {
        if (!ok) return; // gagal simpan: biarkan terbuka agar isian tidak hilang
        tell("sticky");
        closeSelf();
      });
    });

    if (chan) {
      chan.onmessage = function (ev) {
        var m = ev.data || {};
        if (m.id !== ID) return;
        if (m.type === "deleted") closeSelf();
        else if (m.type === "changed" && !dirty) load();
      };
    }

    // Ditutup dengan cara apa pun (mis. Alt+F4): beri tahu halaman Catatan agar penandanya diperbarui.
    window.addEventListener("pagehide", function () {
      if (dirty) save(); // fetch keepalive tetap terkirim setelah halaman ditutup
      tell("sticky");
    });

    setupGrip();
    load();
    // Status jatuh tempo bisa berubah karena waktu berjalan (mis. lewat tengah malam).
    setInterval(function () { if (!dirty) load(); }, 60000);
  });
})();
