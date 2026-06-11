// Pengingat global: perbarui lencana di header + notifikasi browser (opsional).
// Disertakan di semua halaman lewat base.html.
(function () {
  "use strict";

  var POLL_MS = 5 * 60 * 1000; // cek tiap 5 menit
  var LABEL = { overdue: "Lewat tempo", today: "Jatuh tempo hari ini" };

  function todayStr() {
    var d = new Date();
    return d.getFullYear() + "-" + (d.getMonth() + 1) + "-" + d.getDate();
  }

  function updateBadges(n) {
    var badges = document.querySelectorAll(".js-reminder-badge");
    badges.forEach(function (b) {
      if (n > 0) { b.textContent = n > 99 ? "99+" : String(n); b.classList.remove("hidden"); }
      else b.classList.add("hidden");
    });
  }

  function maybeNotify(items) {
    if (!("Notification" in window) || Notification.permission !== "granted") return;
    var day = todayStr();
    (items || []).forEach(function (it) {
      var key = "dailynotif:" + it.id + ":" + day;
      try {
        if (localStorage.getItem(key)) return;
        localStorage.setItem(key, "1");
      } catch (e) { /* localStorage bisa diblokir; lanjut saja */ }
      try {
        new Notification("Pengingat: " + (it.title || "(tanpa judul)"), {
          body: LABEL[it.status] || "Perlu perhatian",
          icon: "/static/img/emblem.png",
          tag: "daily-" + it.id
        });
      } catch (e) { /* abaikan */ }
    });
  }

  function poll() {
    fetch("/api/notes/due")
      .then(function (r) { return r.json(); })
      .then(function (d) {
        updateBadges(d.badge || 0);
        maybeNotify(d.items);
      })
      .catch(function () { /* server mungkin sedang restart; abaikan */ });
  }

  function setupEnableButton() {
    var btn = document.getElementById("enableNotif");
    if (!btn) return;
    if (!("Notification" in window) || Notification.permission !== "default") {
      btn.classList.add("hidden");
      return;
    }
    btn.classList.remove("hidden");
    btn.addEventListener("click", function () {
      Notification.requestPermission().then(function (perm) {
        if (perm !== "default") btn.classList.add("hidden");
        if (perm === "granted") poll();
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    setupEnableButton();
    poll();
    setInterval(poll, POLL_MS);
  });
})();
