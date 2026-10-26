// Checklist di dalam catatan: tampilan + kendali, dipakai halaman Catatan dan sticky desktop.
// Perubahan dikirim per item (centang, ubah, pindah) ke /api/notes/<id>/checklist dan diantrikan
// per catatan, jadi edit dari sticky dan dari halaman Catatan tidak saling menimpa.
(function () {
  "use strict";

  var PRIO_CYCLE = ["tinggi", "sedang", "rendah", null];
  var PRIO_LABEL = { tinggi: "Tinggi", sedang: "Sedang", rendah: "Rendah" };
  var TEXT_DELAY = 600;
  var RETRY_DELAY = 5000;

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  // Id item: 12 karakter heksadesimal (cocok dengan pola di server).
  function newId() {
    var a = new Uint8Array(6);
    (window.crypto || window.msCrypto).getRandomValues(a);
    return Array.prototype.map.call(a, function (b) { return ("0" + b.toString(16)).slice(-2); }).join("");
  }

  function filled(note) { return (note && note.checklist || []).filter(function (i) { return i.text; }); }
  function progress(note) {
    var items = filled(note);
    return { done: items.filter(function (i) { return i.done; }).length, total: items.length };
  }
  function allDone(note) { var p = progress(note); return p.total > 0 && p.done === p.total; }

  function prioLabel(p) { return PRIO_LABEL[p] || ""; }

  // Label prioritas lengkap + singkatan satu huruf (sticky sempit hanya menampilkan singkatan).
  function prioText(p) {
    return '<span class="cl-lbl">' + prioLabel(p) + '</span><span class="cl-ab" aria-hidden="true">' + prioLabel(p).charAt(0) + "</span>";
  }

  function rowHtml(it, o) {
    var name = it.text || "item kosong";
    if (o.readonly) {
      return '<li class="cl-item' + (it.done ? " is-done" : "") + '" data-level="' + it.level + '">' +
        '<span class="cl-box" aria-hidden="true">' + o.icon(it.done ? "checkbox" : "square") + "</span>" +
        '<span class="cl-ro">' + esc(it.text) + (it.done ? '<span class="sr-only"> (selesai)</span>' : "") + "</span>" +
        (it.priority ? '<span class="cl-flag prio-' + it.priority + '">' + o.icon("flag") + "<span>" + prioLabel(it.priority) + "</span></span>" : "") +
        "</li>";
    }
    var prioName = it.priority ? prioLabel(it.priority) : "tanpa";
    return '<li class="cl-item' + (it.done ? " is-done" : "") + '" data-cl-item="' + it.id + '" data-level="' + it.level + '">' +
      // Pegangan: klik = menu pindah, seret = pindah langsung. Keyboard memakai Alt+↑/↓ dan Tab
      // di kolom teks, jadi pegangan tidak menambah perhentian Tab.
      '<button type="button" class="cl-handle" data-cl="handle" tabindex="-1" aria-haspopup="menu" aria-expanded="false" aria-label="Pindah item: ' +
        esc(name) + '" title="Klik untuk memindah, atau seret. Keyboard: Alt+↑/↓">' + o.icon("grip-vertical") + "</button>" +
      '<input type="checkbox" class="cl-check" data-cl="check"' + (it.done ? " checked" : "") + ' aria-label="Selesai: ' + esc(name) + '">' +
      '<input type="text" class="cl-text" data-cl="text" maxlength="500" value="' + esc(it.text) + '" placeholder="Item" aria-label="' +
        (it.level ? "Sub-item" : "Item") + ' checklist" autocomplete="off">' +
      '<button type="button" class="cl-prio' + (it.priority ? " has-prio prio-" + it.priority : "") + '" data-cl="prio" title="Prioritas item: ' +
        prioName + '" aria-label="Prioritas item: ' + prioName + '. Klik untuk mengganti">' + o.icon("flag") +
        (it.priority ? prioText(it.priority) : "") + "</button>" +
      '<button type="button" class="cl-del" data-cl="del" title="Hapus item" aria-label="Hapus item: ' + esc(name) + '">' + o.icon("x") + "</button>" +
      "</li>";
  }

  // o: { icon(nama) -> svg, limit (lipat bila item lebih banyak; 0 = tidak), open (sedang dibuka
  //      penuh), readonly (tampilan arsip), addOpen (tampilkan kolom tambah walau belum ada item),
  //      draft (teks kolom "Tambah item" yang belum dikirim) }
  function html(note, o) {
    var items = note.checklist || [];
    if (!items.length && !o.addOpen && !o.draft) return "";
    var shown = items, more = "";
    if (o.limit && items.length > o.limit + 2) {
      if (!o.open) {
        shown = items.slice(0, o.limit);
        more = '<button type="button" class="cl-more" data-cl="more" aria-expanded="false">' + o.icon("chevron-down") +
          " " + (items.length - o.limit) + " item lagi</button>";
      } else {
        more = '<button type="button" class="cl-more" data-cl="more" aria-expanded="true">' + o.icon("chevron-up") + " Lipat checklist</button>";
      }
    }
    var out = '<div class="cl" data-checklist="' + note.id + '">';
    if (shown.length) out += '<ul class="cl-list">' + shown.map(function (it) { return rowHtml(it, o); }).join("") + "</ul>";
    out += more;
    if (!o.readonly) {
      out += '<div class="cl-new">' + o.icon("plus") +
        '<input type="text" class="cl-newtext" data-cl="new" maxlength="500" placeholder="Tambah item" aria-label="Tambah item checklist" autocomplete="off" value="' +
        esc(o.draft || "") + '"></div>';
    }
    return out + "</div>";
  }

  function itemsOf(note) { return (note && note.checklist) || []; }
  function indexOf(items, id) {
    for (var i = 0; i < items.length; i++) if (items[i].id === id) return i;
    return -1;
  }
  function blockEnd(items, i) {
    var end = i + 1;
    if (items[i].level === 0) while (end < items.length && items[end].level > 0) end++;
    return end;
  }

  // Posisi tujuan naik/turun dalam bentuk operasi "move" (before = id item sesudahnya, null = akhir).
  function stepMove(items, id, dir) {
    var i = indexOf(items, id);
    if (i < 0) return null;
    var it = items[i];
    var end = blockEnd(items, i);
    var j;
    if (it.level === 0) {
      if (dir < 0) {
        for (j = i - 1; j >= 0 && items[j].level > 0; j--);
        return j < 0 ? null : { before: items[j].id, level: 0 };
      }
      if (end >= items.length) return null;
      var after = blockEnd(items, end);
      return { before: after < items.length ? items[after].id : null, level: 0 };
    }
    if (dir < 0) {
      if (items[i - 1].level > 0) return { before: items[i - 1].id, level: 1 };
      // Sub-item pertama naik melewati induknya: jadi sub-item terakhir induk sebelumnya.
      return { before: items[i - 1].id, level: i - 1 > 0 ? 1 : 0 };
    }
    if (i + 1 >= items.length) return null;
    return { before: i + 2 < items.length ? items[i + 2].id : null, level: 1 };
  }

  // ---- Kendali -------------------------------------------------------------------------
  // root: elemen yang memuat satu atau lebih [data-checklist].
  // o: { icon, getNote(id), onChange(note, focus, quiet), onAllDone(note), onMore(id),
  //      reveal(id) (buka checklist yang terlipat), announce(teks), onError(teks), onMissing(id),
  //      scroller (opsional) }
  function Controller(root, o) {
    this.root = root;
    this.o = o;
    this.chain = {};    // id catatan -> Promise permintaan terakhir (berurutan)
    this.inflight = 0;
    this.texts = {};    // id catatan -> { id item: teks belum terkirim }
    this.drafts = {};   // id catatan -> isi kolom "Tambah item" yang belum dikirim
    this.timers = {};
    this.drag = null;
    this.dragJustMoved = false;
    this.menu = null;
    bind(this);
  }

  Controller.prototype.hasPending = function (noteId) {
    return !!Object.keys(this.texts[noteId] || {}).length;
  };

  Controller.prototype.isBusy = function () {
    if (this.menu && !this.menu.el.isConnected) this.menu = null; // hilang karena digambar ulang
    if (this.inflight || this.drag || this.menu) return true;
    for (var k in this.texts) if (Object.keys(this.texts[k]).length) return true;
    var a = document.activeElement;
    return !!(a && document.hasFocus() && this.root.contains(a) && a.closest("[data-checklist]") &&
      (a.getAttribute("data-cl") === "text" || a.getAttribute("data-cl") === "new"));
  };

  // Operasi teks yang belum terkirim (untuk disimpan seketika saat jendela ditutup).
  Controller.prototype.takePending = function (noteId) {
    clearTimeout(this.timers[noteId]);
    var t = this.texts[noteId] || {};
    this.texts[noteId] = {};
    return Object.keys(t).map(function (id) { return { op: "set", id: id, text: t[id] }; });
  };

  // Isi kolom "Tambah item" yang belum dikirim, sebagai operasi "add".
  Controller.prototype.takeDraft = function (noteId) {
    var t = (this.drafts[noteId] || "").trim();
    delete this.drafts[noteId];
    return t ? [{ op: "add", id: newId(), text: t.slice(0, 500), level: 0 }] : [];
  };

  // Hasil: true bila tidak ada lagi teks yang belum tersimpan.
  Controller.prototype.flush = function (noteId) {
    var self = this;
    var p = this.hasPending(noteId) ? this.send(noteId, [], null, true) : (this.chain[noteId] || Promise.resolve());
    return p.then(function () { return !self.hasPending(noteId); });
  };

  // Simpan semuanya (teks tertunda + isi "Tambah item"), mis. sebelum jendela sticky ditutup.
  Controller.prototype.commit = function (noteId) {
    var self = this;
    var text = this.drafts[noteId];
    var ops = this.takeDraft(noteId);
    if (!ops.length) {
      // Commit sebelumnya yang masih berjalan bisa gagal dan mengembalikan drafnya: belum tersimpan.
      return this.flush(noteId).then(function (ok) { return ok && !(self.drafts[noteId] || "").trim(); });
    }
    return this.send(noteId, ops, null, false).then(function (n) {
      if (!n) { self.drafts[noteId] = text; return false; }
      return !self.hasPending(noteId);
    });
  };

  Controller.prototype.flushAll = function () {
    var self = this;
    return Promise.all(Object.keys(this.texts).map(function (id) { return self.flush(id); }));
  };

  Controller.prototype.send = function (noteId, ops, focus, quiet) {
    var self = this;
    var pending = this.takePending(noteId);
    var all = pending.concat(ops);
    if (!all.length) return Promise.resolve(null);
    var before = this.o.getNote(noteId);
    var wasAll = allDone(before);
    // Tawaran "tandai selesai?" hanya setelah pengguna mencentang (atau menghapus) item,
    // bukan karena teks item dikosongkan.
    var acts = ops.some(function (op) { return (op.op === "set" && op.done === true) || op.op === "remove"; });
    this.inflight++;
    var p = (this.chain[noteId] || Promise.resolve()).then(function () {
      return fetch("/api/notes/" + noteId + "/checklist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ops: all }),
        keepalive: true // tetap terkirim walau jendela sticky sedang ditutup
      });
    }).then(function (r) {
      if (r.status === 404) { if (self.o.onMissing) self.o.onMissing(noteId); throw new Error("hilang"); }
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    }).then(function (note) {
      self.inflight--;
      self.apply(note, focus, quiet);
      if (acts && !wasAll && allDone(note) && !note.done && self.o.onAllDone) self.o.onAllDone(note);
      return note;
    }, function (err) {
      self.inflight--;
      if (err && err.message === "hilang") return null;
      // Teks yang gagal terkirim kembali ke antrean (kecuali sudah ada ketikan yang lebih baru)
      // dan dicoba lagi, jadi tidak hilang diam-diam.
      var q = self.texts[noteId] = self.texts[noteId] || {};
      pending.forEach(function (op) { if (!(op.id in q)) q[op.id] = op.text; });
      if (pending.length) {
        clearTimeout(self.timers[noteId]);
        self.timers[noteId] = setTimeout(function () { self.flush(noteId); }, RETRY_DELAY);
      }
      if (self.o.onError) self.o.onError("Checklist gagal disimpan. Coba lagi.");
      return null;
    });
    this.chain[noteId] = p;
    return p;
  };

  // Teks yang belum terkirim ditulis kembali ke kolomnya setelah daftar digambar ulang.
  Controller.prototype.restoreInputs = function (noteId) {
    var t = this.texts[noteId] || {};
    for (var id in t) {
      var input = this.input(noteId, id, "text");
      if (input && input.value !== t[id]) input.value = t[id];
    }
  };

  // Terapkan hasil server ke tampilan, tanpa membuang teks yang sedang diketik.
  Controller.prototype.apply = function (note, focus, quiet) {
    var act = document.activeElement;
    var keep = null, keepNew = null;
    if (act && act.getAttribute("data-cl") === "text") {
      var li = act.closest("[data-cl-item]");
      var box = act.closest("[data-checklist]");
      if (li && box && box.getAttribute("data-checklist") === note.id) {
        keep = { item: li.getAttribute("data-cl-item"), value: act.value, caret: act.selectionStart };
      }
    } else if (act && act.getAttribute("data-cl") === "new") {
      var nb = act.closest("[data-checklist]");
      if (nb && nb.getAttribute("data-checklist") === note.id) keepNew = act.selectionStart;
    }
    this.o.onChange(note, focus, quiet && !focus);
    if (quiet && !focus) return;
    this.restoreInputs(note.id);
    // Teks yang diketik di "Tambah item" selama permintaan berjalan tetap di posisi kursornya.
    if (keepNew != null && (!focus || (focus.part === "new" && focus.caret == null))) {
      focus = { part: "new", caret: keepNew };
    }
    if (keep && (!focus || focus.item === keep.item)) {
      var idx = indexOf(itemsOf(note), keep.item);
      if (idx >= 0 && itemsOf(note)[idx].text !== keep.value) {
        var input = this.input(note.id, keep.item, "text");
        if (input) {
          input.value = keep.value;
          this.queueText(note.id, keep.item, keep.value);
        }
      }
      if (!focus) focus = { item: keep.item, part: "text", caret: keep.caret };
    }
    this.restoreFocus(note.id, focus);
  };

  Controller.prototype.input = function (noteId, itemId, part) {
    var box = this.root.querySelector('[data-checklist="' + noteId + '"]');
    if (!box) return null;
    if (part === "new") return box.querySelector('[data-cl="new"]');
    var li = box.querySelector('[data-cl-item="' + itemId + '"]');
    return li ? li.querySelector('[data-cl="' + (part || "text") + '"]') : null;
  };

  // Item yang tersembunyi di checklist terlipat dibuka dulu sebelum difokus.
  Controller.prototype.reveal = function (noteId, itemId, part) {
    var el = this.input(noteId, itemId, part);
    if (!el && itemId && this.o.reveal && indexOf(itemsOf(this.o.getNote(noteId)), itemId) >= 0) {
      this.o.reveal(noteId);
      el = this.input(noteId, itemId, part);
    }
    return el;
  };

  Controller.prototype.restoreFocus = function (noteId, f) {
    if (!f) return;
    var el = (f.part !== "new" && this.reveal(noteId, f.item, f.part)) || this.input(noteId, null, "new");
    if (!el) return;
    el.focus({ preventScroll: false });
    if (el.type === "text" && f.caret != null) {
      var c = f.caret === "end" ? el.value.length : Math.min(f.caret, el.value.length);
      try { el.setSelectionRange(c, c); } catch (_) { /* abaikan */ }
    }
  };

  Controller.prototype.queueText = function (noteId, itemId, text) {
    var self = this;
    (this.texts[noteId] = this.texts[noteId] || {})[itemId] = text;
    clearTimeout(this.timers[noteId]);
    this.timers[noteId] = setTimeout(function () { self.flush(noteId); }, TEXT_DELAY);
  };

  // Pindah satu langkah / ubah tingkat (dipakai keyboard dan menu pegangan).
  Controller.prototype.moveItem = function (noteId, id, kind, caret) {
    var o = this.o;
    var items = itemsOf(o.getNote(noteId));
    var idx = indexOf(items, id);
    if (idx < 0) return false;
    var focus = { item: id, part: "text", caret: caret };
    if (kind === "up" || kind === "down") {
      var dir = kind === "up" ? -1 : 1;
      var mv = stepMove(items, id, dir);
      if (!mv) return false;
      this.send(noteId, [{ op: "move", id: id, before: mv.before, level: mv.level }], focus);
      o.announce(dir < 0 ? "Item dipindah ke atas" : "Item dipindah ke bawah");
    } else if (kind === "in") {
      if (items[idx].level !== 0 || idx === 0) return false;
      this.send(noteId, [{ op: "set", id: id, level: 1 }], focus);
      o.announce("Menjadi sub-item");
    } else if (kind === "out") {
      if (items[idx].level === 0) return false;
      this.send(noteId, [{ op: "set", id: id, level: 0 }], focus);
      o.announce("Menjadi item utama");
    }
    return true;
  };

  function ctx(el) {
    var box = el.closest("[data-checklist]");
    var li = el.closest("[data-cl-item]");
    return {
      noteId: box && box.getAttribute("data-checklist"),
      itemId: li && li.getAttribute("data-cl-item"),
      li: li
    };
  }

  function neighbourFocus(items, idx) {
    if (idx > 0) return { item: items[idx - 1].id, part: "text", caret: "end" };
    if (items.length > 1) return { item: items[1].id, part: "text", caret: "end" };
    return { part: "new" };
  }

  // ---- Menu pegangan (alternatif klik untuk seret: WCAG 2.5.7) ----------------------------
  var MENU = [
    ["up", "Naik"], ["down", "Turun"], ["in", "Jadikan sub-item"], ["out", "Jadikan item utama"]
  ];

  function closeMenu(self, focusText) {
    var m = self.menu;
    if (!m) return;
    self.menu = null;
    if (m.el.parentNode) m.el.parentNode.removeChild(m.el);
    if (m.handle.isConnected) m.handle.setAttribute("aria-expanded", "false");
    if (focusText) {
      var t = self.input(m.noteId, m.itemId, "text");
      if (t) t.focus();
    }
  }

  function openMenu(self, handle) {
    var c = ctx(handle);
    var items = itemsOf(self.o.getNote(c.noteId));
    var idx = indexOf(items, c.itemId);
    if (idx < 0) return;
    closeMenu(self, false);
    var it = items[idx];
    var allowed = {
      up: !!stepMove(items, it.id, -1),
      down: !!stepMove(items, it.id, 1),
      "in": it.level === 0 && idx > 0,
      out: it.level > 0
    };
    var el = document.createElement("div");
    el.className = "cl-menu";
    el.setAttribute("role", "menu");
    el.setAttribute("aria-label", "Pindah item");
    // Entri yang tidak berlaku memakai aria-disabled (bukan disabled) agar tetap bisa difokus
    // dan terbaca saat menelusuri menu dengan panah.
    el.innerHTML = MENU.map(function (m) {
      return '<button type="button" role="menuitem" data-cl="mv" data-mv="' + m[0] + '"' + (allowed[m[0]] ? "" : ' aria-disabled="true"') + ">" + m[1] + "</button>";
    }).join("");
    c.li.appendChild(el);
    handle.setAttribute("aria-expanded", "true");
    self.menu = { el: el, handle: handle, noteId: c.noteId, itemId: c.itemId };
    // Dibalik ke atas hanya bila muat di dalam area gulir (sticky: badan sticky); luapan ke bawah
    // masih bisa digulir, luapan ke atas tidak.
    var r = el.getBoundingClientRect();
    var sc = self.o.scroller ? self.o.scroller.getBoundingClientRect() : { top: 0, bottom: window.innerHeight };
    if (r.bottom > sc.bottom && c.li.getBoundingClientRect().top - r.height >= sc.top) el.classList.add("up");
    el.scrollIntoView({ block: "nearest" });
    // Klik pada entri tak tersedia atau tepi menu tidak boleh memindahkan fokus keluar menu.
    el.addEventListener("pointerdown", function (e) { e.preventDefault(); });
    (el.querySelector("button:not([aria-disabled])") || el.querySelector("button")).focus();
  }

  function onMenuKey(self, e) {
    var m = self.menu;
    if (!m || !m.el.contains(e.target)) return false;
    var btns = Array.prototype.slice.call(m.el.querySelectorAll("button"));
    var i = btns.indexOf(document.activeElement);
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      var n = btns[(i + (e.key === "ArrowDown" ? 1 : btns.length - 1)) % btns.length];
      if (n) n.focus();
      return true;
    }
    if (e.key === "Tab") { closeMenu(self, false); return false; }
    return false;
  }

  function bind(self) {
    var root = self.root, o = self.o;

    root.addEventListener("change", function (e) {
      var el = e.target;
      if (el.getAttribute("data-cl") !== "check") return;
      var c = ctx(el);
      self.send(c.noteId, [{ op: "set", id: c.itemId, done: el.checked }], { item: c.itemId, part: "check" });
    });

    root.addEventListener("input", function (e) {
      var el = e.target;
      var kind = el.getAttribute("data-cl");
      if (kind === "new") { self.drafts[ctx(el).noteId] = el.value; return; }
      if (kind !== "text") return;
      var c = ctx(el);
      self.queueText(c.noteId, c.itemId, el.value);
      // Nama kotak centang & tombol hapus ikut teks terbaru (pembaca layar).
      var nm = el.value.trim() || "item kosong";
      [["check", "Selesai: "], ["del", "Hapus item: "], ["handle", "Pindah item: "]].forEach(function (p) {
        var b = c.li && c.li.querySelector('[data-cl="' + p[0] + '"]');
        if (b) b.setAttribute("aria-label", p[1] + nm);
      });
    });

    root.addEventListener("focusout", function (e) {
      var el = e.target;
      if (el.getAttribute("data-cl") !== "text") return;
      var c = ctx(el);
      if (!c.noteId) return;
      // Ditunda sejenak: kolom yang hilang karena kartu digambar ulang bukan "ditinggalkan".
      setTimeout(function () {
        if (!el.isConnected || document.activeElement === el) return;
        // Baris yang ditinggalkan kosong dibuang; selain itu teksnya langsung disimpan.
        if (!el.value.trim()) {
          var note = o.getNote(c.noteId);
          var idx = indexOf(itemsOf(note), c.itemId);
          if (idx >= 0 && !itemsOf(note)[idx].text) {
            delete (self.texts[c.noteId] || {})[c.itemId];
            self.send(c.noteId, [{ op: "remove", id: c.itemId }], null);
            return;
          }
        }
        self.flush(c.noteId);
      }, 0);
    });

    root.addEventListener("click", function (e) {
      var btn = e.target.closest("[data-cl]");
      if (!btn || !root.contains(btn)) return;
      var kind = btn.getAttribute("data-cl");
      var c = ctx(btn);
      if (kind === "more") { if (o.onMore) o.onMore(c.noteId); return; }
      if (kind === "handle") {
        // Klik setelah seret sungguhan bukan permintaan membuka menu.
        if (self.dragJustMoved) { self.dragJustMoved = false; return; }
        if (self.menu && self.menu.handle === btn) closeMenu(self, true);
        else openMenu(self, btn);
        return;
      }
      if (kind === "mv") {
        if (btn.getAttribute("aria-disabled") === "true") return;
        var m = self.menu;
        closeMenu(self, false);
        if (m) {
          var t = self.input(m.noteId, m.itemId, "text");
          if (t) self.queueText(m.noteId, m.itemId, t.value);
          self.moveItem(m.noteId, m.itemId, btn.getAttribute("data-mv"), null);
        }
        return;
      }
      var note = o.getNote(c.noteId);
      var items = itemsOf(note);
      var idx = indexOf(items, c.itemId);
      if (idx < 0) return;
      if (kind === "prio") {
        var cur = items[idx].priority || null;
        var next = PRIO_CYCLE[(PRIO_CYCLE.indexOf(cur) + 1) % PRIO_CYCLE.length];
        self.send(c.noteId, [{ op: "set", id: c.itemId, priority: next }], { item: c.itemId, part: "prio" });
        o.announce("Prioritas item: " + (next ? prioLabel(next) : "tanpa prioritas"));
      } else if (kind === "del") {
        self.send(c.noteId, [{ op: "remove", id: c.itemId }], neighbourFocus(items, idx));
        o.announce("Item dihapus");
      }
    });

    root.addEventListener("keydown", function (e) {
      if (onMenuKey(self, e)) return;
      var el = e.target;
      var kind = el.getAttribute && el.getAttribute("data-cl");
      if (kind === "new") { onNewKey(self, e, el); return; }
      if (kind !== "text" || e.isComposing) return;
      var c = ctx(el);
      var note = o.getNote(c.noteId);
      var items = itemsOf(note);
      var idx = indexOf(items, c.itemId);
      if (idx < 0) return;
      var it = items[idx];
      var send = function (ops, focus) { e.preventDefault(); self.queueText(c.noteId, c.itemId, el.value); self.send(c.noteId, ops, focus); };
      if (e.key === "Enter" && !e.shiftKey && !e.altKey && !e.ctrlKey) {
        if (!el.value.trim()) {
          e.preventDefault();
          if (it.level > 0) send([{ op: "set", id: it.id, level: 0 }], { item: it.id, part: "text" });
          else { var nw = self.input(c.noteId, null, "new"); if (nw) nw.focus(); }
          return;
        }
        var id = newId();
        send([{ op: "add", id: id, after: it.id, text: "", level: it.level }], { item: id, part: "text", caret: 0 });
      } else if (e.key === "Backspace" && !el.value && el.selectionStart === 0) {
        delete (self.texts[c.noteId] || {})[it.id];
        e.preventDefault();
        self.send(c.noteId, [{ op: "remove", id: it.id }], neighbourFocus(items, idx));
      } else if (e.key === "Tab" && !e.altKey && !e.ctrlKey) {
        if ((!e.shiftKey && it.level === 0 && idx > 0) || (e.shiftKey && it.level > 0)) {
          e.preventDefault();
          self.queueText(c.noteId, c.itemId, el.value);
          self.moveItem(c.noteId, it.id, e.shiftKey ? "out" : "in", el.selectionStart);
        }
      } else if ((e.key === "ArrowUp" || e.key === "ArrowDown") && e.altKey) {
        e.preventDefault();
        self.queueText(c.noteId, c.itemId, el.value);
        self.moveItem(c.noteId, it.id, e.key === "ArrowUp" ? "up" : "down", el.selectionStart);
      } else if ((e.key === "ArrowUp" || e.key === "ArrowDown") && !e.shiftKey && !e.ctrlKey) {
        var target = e.key === "ArrowUp" ? items[idx - 1] : items[idx + 1];
        var next = target ? self.reveal(c.noteId, target.id, "text") : (e.key === "ArrowDown" ? self.input(c.noteId, null, "new") : null);
        if (next) { e.preventDefault(); next.focus(); }
      }
    });

    root.addEventListener("pointerdown", function (e) {
      var h = e.target.closest('[data-cl="handle"]');
      if (h && root.contains(h)) startDrag(self, e, h);
    });
    document.addEventListener("pointermove", function (e) { moveDrag(self, e); });
    document.addEventListener("pointerup", function (e) { endDrag(self, e, true); });
    document.addEventListener("pointercancel", function (e) { endDrag(self, e, false); });
    // Klik di luar menu pegangan menutupnya.
    document.addEventListener("pointerdown", function (e) {
      if (self.menu && !self.menu.el.contains(e.target) && e.target !== self.menu.handle && !self.menu.handle.contains(e.target)) closeMenu(self, false);
    }, true);
    window.addEventListener("blur", function () { endDrag(self, null, false); });
    // Esc membatalkan seret / menutup menu (fase capture: tidak diteruskan ke Esc → Beranda).
    window.addEventListener("keydown", function (e) {
      if (e.key !== "Escape") return;
      if (self.drag) { endDrag(self, null, false); e.preventDefault(); e.stopPropagation(); }
      else if (self.menu) { closeMenu(self, true); e.preventDefault(); e.stopPropagation(); }
    }, true);
  }

  function onNewKey(self, e, el) {
    if (e.key !== "Enter" || e.isComposing) return;
    e.preventDefault();
    var text = el.value.trim();
    if (!text) return;
    var noteId = ctx(el).noteId;
    el.value = "";
    delete self.drafts[noteId];
    self.send(noteId, [{ op: "add", id: newId(), text: text, level: 0 }], { part: "new" });
    self.o.announce("Item ditambahkan");
  }

  // ---- Seret item (pegangan bertitik) -------------------------------------------------
  function startDrag(self, e, handle) {
    if (e.button !== 0) return;
    e.preventDefault();
    e.stopPropagation(); // jangan sampai memulai seret kartu ke desktop
    self.dragJustMoved = false;
    var li = handle.closest("[data-cl-item]");
    var list = li.parentNode;
    var rows = Array.prototype.filter.call(list.children, function (r) { return r.hasAttribute("data-cl-item"); });
    var i = rows.indexOf(li);
    var end = i + 1;
    if (li.getAttribute("data-level") === "0") while (end < rows.length && rows[end].getAttribute("data-level") !== "0") end++;
    var noteId = li.closest("[data-checklist]").getAttribute("data-checklist");
    var id = li.getAttribute("data-cl-item");
    // Checklist terlipat: "di bawah baris terakhir yang tampil" berarti sebelum item tersembunyi
    // pertama, bukan akhir seluruh daftar (item itu akan ikut tersembunyi).
    var data = itemsOf(self.o.getNote(noteId));
    var tail = null;
    if (rows.length < data.length) {
      var di = indexOf(data, id);
      var de = di < 0 ? di : blockEnd(data, di);
      var from = indexOf(data, rows[rows.length - 1].getAttribute("data-cl-item")) + 1;
      var nextFrom = function (top) {
        for (var k = from; k < data.length; k++) {
          if ((k >= di && k < de) || (top && data[k].level > 0)) continue;
          return data[k].id;
        }
        return null;
      };
      tail = { 0: nextFrom(true), 1: nextFrom(false) };
    }
    var marker = document.createElement("li");
    marker.className = "cl-drop";
    marker.setAttribute("aria-hidden", "true");
    self.drag = {
      noteId: noteId, id: id, level: +li.getAttribute("data-level"), tail: tail, shown: rows.length,
      list: list, block: rows.slice(i, end), rest: rows.filter(function (r, k) { return k < i || k >= end; }),
      marker: marker, x0: e.clientX, y0: e.clientY, pid: e.pointerId, handle: handle, target: null, moved: false
    };
    try { handle.setPointerCapture(e.pointerId); } catch (_) { /* tetap jalan tanpa capture */ }
  }

  function moveDrag(self, e) {
    var d = self.drag;
    if (!d || e.pointerId !== d.pid) return;
    if (!(e.buttons & 1)) { endDrag(self, e, false); return; }
    if (!d.moved) {
      // Getaran kecil saat mengeklik pegangan bukan seret.
      if (Math.abs(e.clientX - d.x0) < 4 && Math.abs(e.clientY - d.y0) < 4) return;
      d.moved = true;
      closeMenu(self, false);
      d.block.forEach(function (r) { r.classList.add("cl-dragging"); });
      document.body.classList.add("is-dragging-item");
    }
    var before = null, prev = null;
    for (var k = 0; k < d.rest.length; k++) {
      var rc = d.rest[k].getBoundingClientRect();
      if (e.clientY < rc.top + rc.height / 2) { before = d.rest[k]; break; }
      prev = d.rest[k];
    }
    // Geser ke kanan = jadi sub-item; hanya bila ada item di atas posisi tujuan.
    var dx = e.clientX - d.x0;
    var level = prev && (dx > 24 || (d.level > 0 && dx > -24)) ? 1 : 0;
    d.target = { before: before ? before.getAttribute("data-cl-item") : (d.tail ? d.tail[level] : null), level: level };
    d.marker.setAttribute("data-level", String(level));
    d.list.insertBefore(d.marker, before || null);
    autoScroll(self, e.clientY);
  }

  function autoScroll(self, y) {
    var sc = self.o.scroller;
    if (!sc) return;
    var r = sc.getBoundingClientRect();
    if (y < r.top + 24) sc.scrollTop -= 8;
    else if (y > r.bottom - 24) sc.scrollTop += 8;
  }

  function endDrag(self, e, commit) {
    var d = self.drag;
    if (!d || (e && e.pointerId !== undefined && e.pointerId !== d.pid)) return;
    self.drag = null;
    self.dragJustMoved = d.moved;
    try { d.handle.releasePointerCapture(d.pid); } catch (_) { /* sudah dilepas */ }
    if (d.marker.parentNode) d.marker.parentNode.removeChild(d.marker);
    d.block.forEach(function (r) { r.classList.remove("cl-dragging"); });
    document.body.classList.remove("is-dragging-item");
    if (!commit || !d.moved || !d.target) return;
    var items = itemsOf(self.o.getNote(d.noteId));
    var i = indexOf(items, d.id);
    if (i < 0) return;
    var end = blockEnd(items, i);
    var sameSpot = (d.target.before === (end < items.length ? items[end].id : null)) && d.target.level === d.level;
    if (sameSpot) return;
    self.send(d.noteId, [{ op: "move", id: d.id, before: d.target.before, level: d.target.level }], null).then(function (n) {
      // Checklist terlipat: item yang jatuh di balik lipatan (mis. setelah sub-item tersembunyi) dibuka.
      if (n && d.tail && self.o.reveal && indexOf(itemsOf(n), d.id) >= d.shown) self.o.reveal(d.noteId);
    });
    self.o.announce("Item dipindah");
  }

  window.DailyChecklist = {
    html: html,
    progress: progress,
    allDone: allDone,
    prioLabel: prioLabel,
    newId: newId,
    Controller: Controller
  };
})();
