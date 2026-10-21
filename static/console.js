// Perilaku bersama tema konsol (semua halaman): jam, suara navigasi opsional, Esc ke Beranda.
(function () {
  "use strict";

  // ---- Jam di bilah atas ----
  function tick() {
    var el = document.getElementById("clock");
    if (!el) return;
    var d = new Date();
    el.textContent = String(d.getHours()).padStart(2, "0") + ":" + String(d.getMinutes()).padStart(2, "0");
    el.setAttribute("datetime", d.toISOString());
  }

  // ---- Suara navigasi: klik halus buatan Web Audio, menyala secara bawaan (bisa dimatikan) ----
  var KEY = "dailyapp:sound";
  var ctx = null;
  var lastPlay = 0;
  function soundOn() {
    // Belum pernah diatur = menyala; "0" = dimatikan lewat tombol speaker.
    try { return localStorage.getItem(KEY) !== "0"; } catch (e) { return true; }
  }
  function play(kind) {
    if (!soundOn()) return;
    // Saat kursor disapukan cepat melintasi tile, bunyi jangan bertumpuk.
    var now = Date.now();
    if (kind === "move" && now - lastPlay < 45) return;
    lastPlay = now;
    try {
      ctx = ctx || new (window.AudioContext || window.webkitAudioContext)();
      var o = ctx.createOscillator(), g = ctx.createGain(), t = ctx.currentTime;
      o.type = "sine";
      o.frequency.setValueAtTime(kind === "select" ? 660 : 520, t);
      if (kind === "select") o.frequency.exponentialRampToValueAtTime(880, t + 0.07);
      g.gain.setValueAtTime(0.0001, t);
      g.gain.exponentialRampToValueAtTime(0.05, t + 0.008);
      g.gain.exponentialRampToValueAtTime(0.0001, t + (kind === "select" ? 0.12 : 0.06));
      o.connect(g).connect(ctx.destination);
      o.start(t);
      o.stop(t + 0.14);
    } catch (e) { /* audio tidak tersedia: diam saja */ }
  }
  window.DailySound = { play: play };

  // Ikon sprite untuk HTML yang dibangun di JS: DailyIcon("download") → <svg …>.
  window.DailyIcon = function (name, cls) {
    return '<svg class="ico ' + (cls || "") + '" aria-hidden="true" focusable="false">' +
      '<use href="/static/vendor/tabler-sprite.svg#' + name + '"></use></svg>';
  };

  function syncSoundButton() {
    var btn = document.getElementById("soundToggle");
    if (!btn) return;
    var on = soundOn();
    btn.setAttribute("aria-pressed", String(on));
    btn.setAttribute("aria-label", on ? "Matikan suara navigasi" : "Nyalakan suara navigasi");
    btn.title = btn.getAttribute("aria-label");
    btn.querySelector("use").setAttribute("href", "/static/vendor/tabler-sprite.svg#" + (on ? "volume" : "volume-off"));
  }

  // ---- Esc: kembali ke Beranda ----
  function isEditing(el) {
    if (!el) return false;
    var tag = el.tagName;
    return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || tag === "CANVAS" || el.isContentEditable;
  }
  function formOpen() {
    // Form yang sedang terbuka (Catatan/Invoice) diberi data-esc-guard: Esc tidak boleh
    // membuang isian yang belum disimpan.
    var guards = document.querySelectorAll("[data-esc-guard]");
    for (var i = 0; i < guards.length; i++) {
      if (!guards[i].classList.contains("hidden")) return true;
    }
    return false;
  }

  document.addEventListener("keydown", function (ev) {
    if (ev.key !== "Escape" || ev.defaultPrevented || location.pathname === "/") return;
    if (isEditing(document.activeElement) || formOpen()) return;
    play("select");
    location.href = "/";
  });

  document.addEventListener("DOMContentLoaded", function () {
    tick();
    setInterval(tick, 20000);
    syncSoundButton();
    var btn = document.getElementById("soundToggle");
    if (btn) {
      btn.addEventListener("click", function () {
        try { localStorage.setItem(KEY, soundOn() ? "0" : "1"); } catch (e) { /* abaikan */ }
        syncSoundButton();
        play("select");
      });
    }
  });
})();
