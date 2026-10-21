// Invoice Generator — multi-brand: daftar invoice, form (kalkulasi live), klien, brand & desain (vanilla JS).
(function () {
  "use strict";

  var $ = function (id) { return document.getElementById(id); };
  var DESIGNS = window.INVOICE_DESIGNS || [];
  var DESIGN_BY_ID = {};
  DESIGNS.forEach(function (d) { DESIGN_BY_ID[d.id] = d; });
  var TABS = ["invoices", "clients", "brands"];

  var state = { brands: [], default_brand_id: "", clients: [], invoices: [] };
  var BRAND_BY_ID = {};
  var editingId = null;       // id invoice yang sedang diedit (null = baru)
  var numberAuto = true;      // nomor masih otomatis (belum diketik manual)
  var dueAuto = true;         // jatuh tempo masih mengikuti tanggal + N hari
  var formBrandId = "";
  var formDesign = "";
  var formColor = "";         // "" = warna bawaan desain
  var brandDesign = "";
  var brandColor = "";
  var pendingLogo = null;     // logo dipilih untuk brand yang belum disimpan

  // -------------------------------------------------------------------------
  // Util
  // -------------------------------------------------------------------------
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  function num(v) {
    var n = parseFloat(String(v == null ? "" : v).replace(",", "."));
    return isFinite(n) ? n : 0;
  }
  function digits(v) { return parseInt(String(v || "").replace(/\D/g, ""), 10) || 0; }
  function rp(n) { return "Rp " + Math.round(n).toLocaleString("id-ID"); }
  function grouped(n) { return n ? Math.round(n).toLocaleString("id-ID") : ""; }
  function initial(name) { return (String(name || "?").trim()[0] || "?").toUpperCase(); }

  var BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus",
               "September", "Oktober", "November", "Desember"];
  var ROMAWI = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"];
  function tanggal(iso) {
    var p = String(iso || "").split("-");
    if (p.length !== 3) return iso || "";
    return (+p[2]) + " " + BULAN[(+p[1]) - 1] + " " + p[0];
  }
  function isoToday() {
    var t = new Date();
    return t.getFullYear() + "-" + String(t.getMonth() + 1).padStart(2, "0") + "-" + String(t.getDate()).padStart(2, "0");
  }
  function addDays(iso, days) {
    var p = String(iso).split("-");
    var d = new Date(+p[0], (+p[1]) - 1, +p[2] + (+days || 0));
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
  }

  var SATUAN = ["", "satu", "dua", "tiga", "empat", "lima", "enam", "tujuh", "delapan", "sembilan", "sepuluh", "sebelas"];
  function _tb(n) {
    if (n < 12) return SATUAN[n];
    if (n < 20) return SATUAN[n - 10] + " belas";
    if (n < 100) return (SATUAN[Math.floor(n / 10)] + " puluh " + _tb(n % 10)).trim();
    if (n < 200) return ("seratus " + _tb(n - 100)).trim();
    if (n < 1000) return (SATUAN[Math.floor(n / 100)] + " ratus " + _tb(n % 100)).trim();
    if (n < 2000) return ("seribu " + _tb(n - 1000)).trim();
    var units = [[1e12, "triliun"], [1e9, "miliar"], [1e6, "juta"], [1e3, "ribu"]];
    for (var i = 0; i < units.length; i++) {
      if (n >= units[i][0]) return (_tb(Math.floor(n / units[i][0])) + " " + units[i][1] + " " + _tb(n % units[i][0])).trim();
    }
    return "";
  }
  function terbilang(n) {
    n = Math.round(n);
    if (!n) return "nol rupiah";
    var t = _tb(Math.abs(n)) + " rupiah";
    return (n < 0 ? "minus " : "") + t;
  }

  function api(method, url, body) {
    var opt = { method: method, headers: {} };
    if (body !== undefined) {
      opt.headers["Content-Type"] = "application/json";
      opt.body = JSON.stringify(body);
    }
    return fetch(url, opt).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (data) {
        if (!r.ok) throw new Error(data.error || ("Gagal (" + r.status + ")"));
        return data;
      });
    });
  }

  var toastTimer;
  function toast(msg) {
    var el = $("toast");
    el.textContent = msg;
    el.classList.remove("hidden");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { el.classList.add("hidden"); }, 2800);
  }

  function brandOf(id) { return BRAND_BY_ID[id] || BRAND_BY_ID[state.default_brand_id] || null; }
  function multiBrand() { return state.brands.length > 1; }
  function logoUrl(b) { return "/api/invoice/brands/" + encodeURIComponent(b.id) + "/logo?t=" + Date.now(); }

  // -------------------------------------------------------------------------
  // Tab
  // -------------------------------------------------------------------------
  function showTab(name) {
    if (TABS.indexOf(name) === -1) name = "invoices";
    document.querySelectorAll(".inv-tab").forEach(function (b) {
      b.setAttribute("aria-selected", b.dataset.tab === name ? "true" : "false");
    });
    TABS.forEach(function (t) { $("tab-" + t).classList.toggle("hidden", t !== name); });
    try { sessionStorage.setItem("invoiceTab", name); } catch (e) { /* abaikan */ }
  }
  document.querySelectorAll(".inv-tab").forEach(function (b) {
    b.addEventListener("click", function () { showTab(b.dataset.tab); });
  });

  // -------------------------------------------------------------------------
  // Muat data
  // -------------------------------------------------------------------------
  function showLoadMessage(html) {
    ["invList", "clientList", "brandList"].forEach(function (id) {
      $(id).innerHTML = '<div class="bg-white rounded-lg p-6 text-center text-slate-600 border border-slate-200 sm:col-span-2" role="status">' + html + "</div>";
    });
    ["invEmpty", "clientEmpty", "brandEmpty"].forEach(function (id) { $(id).classList.add("hidden"); });
  }

  function load() {
    return api("GET", "/api/invoice/state").then(function (data) {
      state = data;
      BRAND_BY_ID = {};
      state.brands.forEach(function (b) { BRAND_BY_ID[b.id] = b; });
      renderBrandFilter();
      renderSummary();
      renderInvoices();
      renderClients();
      renderClientPick();
      renderBrands();
      $("profileHint").classList.toggle("hidden", state.brands.length > 0);
    });
  }

  // -------------------------------------------------------------------------
  // Thumbnail desain
  // -------------------------------------------------------------------------
  function thumbHtml(id) {
    var src = document.querySelector('#thumbs [data-thumb="' + id + '"]');
    return src ? src.innerHTML : '<div class="thumb"></div>';
  }
  function colorFor(id, chosen) {
    var d = DESIGN_BY_ID[id];
    if (!d) return "#333333";
    return d.uses_accent && chosen ? chosen : d.default_color;
  }

  function renderDesignGrid(container, selected, chosenColor, onPick, sampleBrandId) {
    container.innerHTML = DESIGNS.map(function (d) {
      var sample = "";
      if (sampleBrandId !== null) {
        sample = '<a class="js-sample block text-[11px] text-blue-600 hover:underline text-center" target="_blank" ' +
          'href="/api/invoice/designs/' + encodeURIComponent(d.id) + '/sample.pdf?brand_id=' +
          encodeURIComponent(sampleBrandId || "") + "&color=" + encodeURIComponent(d.uses_accent ? chosenColor : "") +
          '">Contoh PDF</a>';
      }
      return '<div class="design-card rounded-md border border-slate-200 p-1.5 bg-white cursor-pointer hover:border-blue-400" ' +
        'role="radio" tabindex="0" aria-checked="' + (d.id === selected) + '" aria-label="Desain ' + esc(d.name) + '" ' +
        'data-id="' + esc(d.id) + '" data-selected="' + (d.id === selected) + '" title="' + esc(d.description) + '" ' +
        'style="--acc:' + esc(colorFor(d.id, chosenColor)) + '">' +
        thumbHtml(d.id) +
        '<div class="text-xs font-medium text-slate-700 mt-1.5 text-center">' + esc(d.name) + '</div>' + sample + '</div>';
    }).join("");
    container.querySelectorAll(".design-card").forEach(function (card) {
      card.addEventListener("click", function (ev) {
        if (ev.target.closest(".js-sample")) return;
        onPick(card.dataset.id);
      });
      card.addEventListener("keydown", function (ev) {
        if (ev.target !== card || (ev.key !== "Enter" && ev.key !== " ")) return;
        ev.preventDefault();
        onPick(card.dataset.id);
      });
    });
  }

  function syncColorInput(input, wrap, designId, chosen) {
    var d = DESIGN_BY_ID[designId];
    wrap.classList.toggle("invisible", !(d && d.uses_accent));
    input.value = colorFor(designId, chosen);
  }

  // -------------------------------------------------------------------------
  // Ringkasan & daftar invoice
  // -------------------------------------------------------------------------
  function renderBrandFilter() {
    var sel = $("invBrand"), cur = sel.value;
    sel.innerHTML = '<option value="">Semua brand</option>' + state.brands.map(function (b) {
      return '<option value="' + esc(b.id) + '">' + esc(b.name) + "</option>";
    }).join("");
    sel.value = BRAND_BY_ID[cur] ? cur : "";
    sel.classList.toggle("hidden", !multiBrand());
  }

  function renderSummary() {
    var brandFilter = $("invBrand").value;
    var unpaid = 0, unpaidSum = 0, overdue = 0;
    state.invoices.forEach(function (i) {
      if (brandFilter && i.brand_id !== brandFilter) return;
      if (i.effective_status !== "paid") { unpaid++; unpaidSum += i.totals.total; }
      if (i.effective_status === "overdue") overdue++;
    });
    var html = "";
    if (unpaid) html += '<span class="bg-amber-100 text-amber-700 font-semibold px-2 py-1 rounded-full">' + unpaid + " belum lunas · " + rp(unpaidSum) + "</span>";
    if (overdue) html += '<span class="bg-red-100 text-red-700 font-semibold px-2 py-1 rounded-full">' + overdue + " lewat jatuh tempo</span>";
    $("summary").innerHTML = html;
  }

  var STATUS_BADGE = {
    paid: ["Lunas", "bg-green-100 text-green-700"],
    unpaid: ["Belum lunas", "bg-amber-100 text-amber-700"],
    overdue: ["Lewat tempo", "bg-red-100 text-red-700"]
  };

  function renderInvoices() {
    var q = $("invQ").value.trim().toLowerCase();
    var st = $("invStatus").value;
    var brandFilter = $("invBrand").value;
    var list = state.invoices.filter(function (i) {
      if (brandFilter && i.brand_id !== brandFilter) return false;
      if (st === "unpaid" && i.effective_status === "paid") return false;
      if (st && st !== "unpaid" && i.effective_status !== st) return false;
      if (!q) return true;
      return (i.number + " " + (i.client && i.client.name)).toLowerCase().indexOf(q) !== -1;
    });
    $("invEmpty").classList.toggle("hidden", list.length > 0);
    if (!state.invoices.length) $("invEmpty").innerHTML = 'Belum ada invoice. Klik <b>Buat Invoice</b> untuk membuat yang pertama.';
    else $("invEmpty").textContent = "Tidak ada invoice untuk filter ini.";
    $("invList").innerHTML = list.map(function (i) {
      var b = STATUS_BADGE[i.effective_status] || STATUS_BADGE.unpaid;
      var design = DESIGN_BY_ID[i.design];
      var brand = BRAND_BY_ID[i.brand_id];
      var paid = i.status === "paid";
      return '<div class="bg-white rounded-lg border border-slate-200 p-4 flex flex-wrap items-center gap-x-4 gap-y-2" data-id="' + esc(i.id) + '">' +
        '<div class="min-w-0 flex-1">' +
          '<div class="flex flex-wrap items-center gap-2">' +
            '<span class="font-mono font-semibold text-slate-900 break-all">' + esc(i.number) + '</span>' +
            '<span class="text-[11px] font-semibold px-2 py-0.5 rounded-full ' + b[1] + '">' + b[0] + '</span>' +
            (multiBrand() && brand ? '<span class="text-[11px] font-medium px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">' + esc(brand.name) + '</span>' : "") +
            (design ? '<span class="text-[11px] text-slate-500">· ' + esc(design.name) + '</span>' : "") +
          '</div>' +
          '<div class="text-sm text-slate-700 truncate">' + esc(i.client && i.client.name) + '</div>' +
          '<div class="text-xs text-slate-500">' + esc(tanggal(i.date)) + ' · jatuh tempo ' + esc(tanggal(i.due_date)) + '</div>' +
        '</div>' +
        '<div class="text-right font-semibold text-slate-900 whitespace-nowrap">' + rp(i.totals.total) + '</div>' +
        '<div class="flex flex-wrap gap-1 text-sm">' +
          '<a class="inline-flex items-center gap-1 px-2 py-1 rounded border border-slate-300 hover:bg-slate-50" target="_blank" href="/api/invoices/' + encodeURIComponent(i.id) + '/pdf" title="Buka PDF" aria-label="Buka PDF">' + DailyIcon("external-link") + ' PDF</a>' +
          '<a class="inline-flex items-center gap-1 px-2 py-1 rounded border border-slate-300 hover:bg-slate-50" href="/api/invoices/' + encodeURIComponent(i.id) + '/pdf?download=1" title="Unduh PDF" aria-label="Unduh PDF">' + DailyIcon("download") + '<span class="sm:sr-only">Unduh</span></a>' +
          '<button type="button" data-act="edit" class="inline-flex items-center gap-1 px-2 py-1 rounded border border-slate-300 hover:bg-slate-50" title="Edit" aria-label="Edit invoice">' + DailyIcon("pencil") + '<span class="sm:sr-only">Edit</span></button>' +
          '<button type="button" data-act="dup" class="inline-flex items-center gap-1 px-2 py-1 rounded border border-slate-300 hover:bg-slate-50" title="Duplikat" aria-label="Duplikat invoice">' + DailyIcon("copy") + '<span class="sm:sr-only">Duplikat</span></button>' +
          '<button type="button" data-act="paid" class="inline-flex items-center gap-1 px-2 py-1 rounded border border-slate-300 hover:bg-slate-50" title="' + (paid ? "Tandai belum lunas" : "Tandai lunas") + '" aria-label="' + (paid ? "Tandai belum lunas" : "Tandai lunas") + '">' + DailyIcon(paid ? "arrow-back-up" : "check") + '<span class="sm:sr-only">' + (paid ? "Belum lunas" : "Lunas") + '</span></button>' +
          '<button type="button" data-act="del" class="inline-flex items-center gap-1 px-2 py-1 rounded border border-slate-300 hover:bg-red-50 text-red-600" title="Hapus" aria-label="Hapus invoice">' + DailyIcon("trash") + '<span class="sm:sr-only">Hapus</span></button>' +
        '</div></div>';
    }).join("");
  }

  $("invQ").addEventListener("input", renderInvoices);
  $("invStatus").addEventListener("change", renderInvoices);
  $("invBrand").addEventListener("change", function () { renderSummary(); renderInvoices(); });

  $("invList").addEventListener("click", function (ev) {
    var btn = ev.target.closest("button[data-act]");
    if (!btn) return;
    var id = btn.closest("[data-id]").dataset.id;
    var inv = state.invoices.find(function (i) { return i.id === id; });
    if (!inv) return;
    var act = btn.dataset.act;
    if (act === "edit") openInvoiceForm(inv);
    else if (act === "dup") {
      api("POST", "/api/invoices/" + id + "/duplicate").then(function (dup) {
        return load().then(function () { openInvoiceForm(dup); toast("Invoice diduplikat: " + dup.number); });
      }).catch(function (e) { toast(e.message); });
    } else if (act === "paid") {
      api("POST", "/api/invoices/" + id + "/status", { status: inv.status === "paid" ? "unpaid" : "paid" })
        .then(load).then(function () { toast("Status diperbarui"); })
        .catch(function (e) { toast(e.message); });
    } else if (act === "del") {
      if (!confirm("Hapus invoice " + inv.number + "? Tindakan ini tidak bisa dibatalkan.")) return;
      api("DELETE", "/api/invoices/" + id).then(load).then(function () { toast("Invoice dihapus"); })
        .catch(function (e) { toast(e.message); });
    }
  });

  // -------------------------------------------------------------------------
  // Form invoice
  // -------------------------------------------------------------------------
  function itemRowHtml(it) {
    it = it || { desc: "", qty: 1, unit: "", price: 0 };
    return '<tr class="border-b border-slate-100 align-top">' +
      '<td class="py-1.5 pr-2"><textarea rows="1" class="inp js-desc resize-y" placeholder="Nama barang / jasa">' + esc(it.desc) + '</textarea></td>' +
      '<td class="py-1.5 px-2"><input type="number" min="0" step="any" class="inp js-qty" value="' + esc(it.qty) + '"></td>' +
      '<td class="py-1.5 px-2"><input class="inp js-unit" placeholder="pcs" value="' + esc(it.unit) + '"></td>' +
      '<td class="py-1.5 px-2"><input inputmode="numeric" class="inp js-price text-right" placeholder="0" value="' + esc(grouped(it.price)) + '"></td>' +
      '<td class="py-1.5 px-2 text-right whitespace-nowrap pt-3 js-amount">Rp 0</td>' +
      '<td class="py-1.5 text-center pt-2"><button type="button" class="js-del-item text-slate-500 hover:text-red-600 text-lg" title="Hapus item">&times;</button></td>' +
      '</tr>';
  }

  function addItem(it) {
    $("itemRows").insertAdjacentHTML("beforeend", itemRowHtml(it));
    recalc();
  }

  function readItems() {
    var rows = [];
    $("itemRows").querySelectorAll("tr").forEach(function (tr) {
      rows.push({
        desc: tr.querySelector(".js-desc").value.trim(),
        qty: num(tr.querySelector(".js-qty").value),
        unit: tr.querySelector(".js-unit").value.trim(),
        price: digits(tr.querySelector(".js-price").value)
      });
    });
    return rows;
  }

  function recalc() {
    var subtotal = 0;
    $("itemRows").querySelectorAll("tr").forEach(function (tr) {
      var amount = Math.round(num(tr.querySelector(".js-qty").value) * digits(tr.querySelector(".js-price").value));
      subtotal += amount;
      tr.querySelector(".js-amount").textContent = rp(amount);
    });
    var dType = $("i-discType").value, dVal = num($("i-discVal").value), disc = 0;
    if (dType === "percent") disc = Math.round(subtotal * dVal / 100);
    else if (dType === "amount") disc = Math.round(dVal);
    disc = Math.max(0, Math.min(disc, subtotal));
    var dpp = subtotal - disc;
    var taxOn = $("i-taxOn").checked, rate = num($("i-taxRate").value);
    var tax = taxOn ? Math.round(dpp * rate / 100) : 0;
    var total = dpp + tax;
    $("i-discVal").disabled = dType === "none";
    $("i-taxRate").disabled = !taxOn;
    $("t-sub").textContent = rp(subtotal);
    $("t-discRow").classList.toggle("hidden", !disc);
    $("t-discLbl").textContent = "Diskon" + (dType === "percent" ? " (" + dVal + "%)" : "");
    $("t-disc").textContent = "- " + rp(disc);
    $("t-taxRow").classList.toggle("hidden", !taxOn);
    $("t-taxLbl").textContent = "PPN (" + rate + "%)";
    $("t-tax").textContent = rp(tax);
    $("t-total").textContent = rp(total);
    var words = terbilang(total);
    $("t-words").textContent = "Terbilang: " + words.charAt(0).toUpperCase() + words.slice(1);
  }

  $("itemRows").addEventListener("input", function (ev) {
    if (ev.target.classList.contains("js-price")) {
      // Format ribuan saat mengetik, pertahankan posisi kursor dari kanan.
      var el = ev.target, fromRight = el.value.length - el.selectionStart;
      el.value = grouped(digits(el.value));
      var pos = Math.max(0, el.value.length - fromRight);
      el.setSelectionRange(pos, pos);
    }
    recalc();
  });
  $("itemRows").addEventListener("click", function (ev) {
    if (!ev.target.classList.contains("js-del-item")) return;
    ev.target.closest("tr").remove();
    if (!$("itemRows").children.length) addItem();
    recalc();
  });
  $("btnAddItem").addEventListener("click", function () {
    addItem();
    var rows = $("itemRows").querySelectorAll(".js-desc");
    rows[rows.length - 1].focus();
  });
  ["i-discType", "i-discVal", "i-taxOn", "i-taxRate"].forEach(function (id) {
    $(id).addEventListener("input", recalc);
    $(id).addEventListener("change", recalc);
  });

  function refreshNumber() {
    return api("GET", "/api/invoice/next-number?date=" + encodeURIComponent($("i-date").value) +
               "&brand_id=" + encodeURIComponent(formBrandId))
      .then(function (r) { $("i-number").value = r.number; numberAuto = true; })
      .catch(function (e) { $("invFormMsg").textContent = "Gagal mengambil nomor otomatis: " + e.message; });
  }
  $("btnAutoNum").addEventListener("click", refreshNumber);
  $("i-number").addEventListener("input", function () { numberAuto = false; });
  $("i-due").addEventListener("input", function () { dueAuto = false; });
  $("i-date").addEventListener("change", function () {
    var b = brandOf(formBrandId) || {};
    if (dueAuto) $("i-due").value = addDays($("i-date").value, b.due_days || 0);
    if (numberAuto && !editingId) refreshNumber();
  });

  // --- brand di form invoice ---
  function renderFormBrandPick() {
    $("i-brand").innerHTML = state.brands.map(function (b) {
      return '<option value="' + esc(b.id) + '">' + esc(b.name) + (b.is_default ? " (default)" : "") + "</option>";
    }).join("");
    $("i-brand").value = formBrandId;
  }
  function showFormBrandLogo() {
    var b = brandOf(formBrandId);
    var has = !!(b && b.has_logo);
    $("i-brandLogo").classList.toggle("hidden", !has);
    $("i-brandInitial").classList.toggle("hidden", has);
    $("i-brandInitial").textContent = b ? initial(b.name) : "";
    if (has) $("i-brandLogo").src = logoUrl(b);
  }
  // Isi default dari brand ke form (dipakai untuk invoice baru / saat brand diganti).
  function applyBrandDefaults(b, prev) {
    formDesign = b.design || (DESIGNS[0] && DESIGNS[0].id);
    formColor = b.accent_color || "";
    renderFormDesigns();
    if (!$("i-taxOn").checked) $("i-taxRate").value = b.tax_rate != null ? b.tax_rate : 11;
    var notes = $("i-notes").value.trim();
    if (!notes || (prev && notes === (prev.notes || "").trim())) $("i-notes").value = b.notes || "";
    if (dueAuto) $("i-due").value = addDays($("i-date").value, b.due_days || 0);
    recalc();
  }
  $("i-brand").addEventListener("change", function () {
    var prev = brandOf(formBrandId);
    formBrandId = $("i-brand").value;
    var b = brandOf(formBrandId);
    showFormBrandLogo();
    if (!editingId) applyBrandDefaults(b, prev);
    refreshNumber().then(function () {
      $("i-brandNote").textContent = editingId
        ? "Nomor disesuaikan dengan urutan brand ini."
        : "Nomor, desain, & default lain mengikuti brand ini.";
    });
  });

  // --- klien di form invoice ---
  function setClientFields(c) {
    c = c || {};
    $("c-name").value = c.name || "";
    $("c-address").value = c.address || "";
    $("c-phone").value = c.phone || "";
    $("c-email").value = c.email || "";
    $("c-npwp").value = c.npwp || "";
  }
  function readClientFields() {
    return {
      name: $("c-name").value.trim(), address: $("c-address").value.trim(),
      phone: $("c-phone").value.trim(), email: $("c-email").value.trim(), npwp: $("c-npwp").value.trim()
    };
  }
  function renderClientPick() {
    var cur = $("i-clientId").value;
    $("i-clientPick").innerHTML = '<option value="">Pilih klien tersimpan…</option>' +
      state.clients.map(function (c) {
        return '<option value="' + esc(c.id) + '"' + (c.id === cur ? " selected" : "") + ">" + esc(c.name) + "</option>";
      }).join("");
  }
  $("i-clientPick").addEventListener("change", function () {
    var c = state.clients.find(function (x) { return x.id === $("i-clientPick").value; });
    $("i-clientId").value = c ? c.id : "";
    if (c) setClientFields(c);
  });
  $("btnSaveClient").addEventListener("click", function () {
    var data = readClientFields();
    var id = $("i-clientId").value;
    var req = id ? api("PUT", "/api/invoice/clients/" + id, data) : api("POST", "/api/invoice/clients", data);
    req.then(function (c) {
      $("i-clientId").value = c.id;
      return load().then(function () {
        $("clientSaveMsg").textContent = id ? "Data klien diperbarui ✓" : "Klien disimpan ✓";
        setTimeout(function () { $("clientSaveMsg").textContent = ""; }, 2500);
      });
    }).catch(function (e) { $("invFormMsg").textContent = e.message; });
  });

  // --- desain di form invoice ---
  function pickFormDesign(id) {
    formDesign = id;
    $("i-designs").querySelectorAll(".design-card").forEach(function (c) {
      c.dataset.selected = String(c.dataset.id === id);
      c.setAttribute("aria-checked", String(c.dataset.id === id));
    });
    syncColorInput($("i-color"), $("i-colorWrap"), id, formColor);
  }
  function renderFormDesigns() {
    renderDesignGrid($("i-designs"), formDesign, formColor, pickFormDesign, null);
    syncColorInput($("i-color"), $("i-colorWrap"), formDesign, formColor);
  }
  $("i-color").addEventListener("input", function () {
    formColor = $("i-color").value;
    $("i-designs").querySelectorAll(".design-card").forEach(function (c) {
      c.style.setProperty("--acc", colorFor(c.dataset.id, formColor));
    });
  });
  $("btnColorReset").addEventListener("click", function () { formColor = ""; renderFormDesigns(); });

  function openInvoiceForm(inv, opts) {
    opts = opts || {};
    if (!state.brands.length) {
      toast("Buat brand terlebih dahulu.");
      showTab("brands");
      openBrandForm(null);
      return;
    }
    editingId = inv && inv.id ? inv.id : null;
    var b = brandOf((inv && inv.brand_id) || opts.brandId || $("invBrand").value || state.default_brand_id);
    formBrandId = b.id;
    renderFormBrandPick();
    showFormBrandLogo();
    $("i-brandNote").textContent = "";
    $("invFormTitle").textContent = editingId ? "Edit invoice " + inv.number : "Invoice baru";
    $("invFormMsg").textContent = "";
    $("i-date").value = (inv && inv.date) || isoToday();
    $("i-due").value = (inv && inv.due_date) || addDays($("i-date").value, b.due_days || 0);
    $("i-status").value = (inv && inv.status) || "unpaid";
    $("i-clientId").value = (inv && inv.client_id) || "";
    renderClientPick();
    setClientFields(inv && inv.client);
    $("itemRows").innerHTML = "";
    ((inv && inv.items && inv.items.length) ? inv.items : [null]).forEach(addItem);
    $("i-discType").value = (inv && inv.discount_type) || "none";
    $("i-discVal").value = inv ? (inv.discount_value || 0) : 0;
    $("i-taxOn").checked = !!(inv && inv.tax_enabled);
    $("i-taxRate").value = inv && inv.tax_enabled ? inv.tax_rate : (b.tax_rate != null ? b.tax_rate : 11);
    $("i-notes").value = inv ? (inv.notes || "") : (b.notes || "");
    formDesign = (inv && inv.design) || b.design || (DESIGNS[0] && DESIGNS[0].id);
    formColor = inv ? (inv.accent_color || "") : (b.accent_color || "");
    renderFormDesigns();
    recalc();
    dueAuto = !inv;
    if (inv) { $("i-number").value = inv.number; numberAuto = false; }
    else { $("i-number").value = ""; refreshNumber(); }
    $("invListWrap").classList.add("hidden");
    $("invForm").classList.remove("hidden");
    showTab("invoices");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function closeInvoiceForm() {
    $("invForm").classList.add("hidden");
    $("invListWrap").classList.remove("hidden");
    editingId = null;
  }

  function readInvoiceForm() {
    return {
      brand_id: formBrandId,
      number: $("i-number").value.trim(),
      date: $("i-date").value,
      due_date: $("i-due").value,
      status: $("i-status").value,
      client_id: $("i-clientId").value,
      client: readClientFields(),
      items: readItems(),
      discount_type: $("i-discType").value,
      discount_value: num($("i-discVal").value),
      tax_enabled: $("i-taxOn").checked,
      tax_rate: num($("i-taxRate").value),
      notes: $("i-notes").value,
      design: formDesign,
      accent_color: formColor
    };
  }

  $("btnNewInv").addEventListener("click", function () { openInvoiceForm(null); });
  document.querySelectorAll(".js-inv-cancel").forEach(function (b) { b.addEventListener("click", closeInvoiceForm); });

  $("invForm").addEventListener("submit", function (ev) {
    ev.preventDefault();
    var data = readInvoiceForm();
    $("invFormMsg").textContent = "";
    var req = editingId ? api("PUT", "/api/invoices/" + editingId, data) : api("POST", "/api/invoices", data);
    req.then(function (inv) {
      return load().then(function () {
        closeInvoiceForm();
        toast("Invoice " + inv.number + " disimpan");
      });
    }).catch(function (e) { $("invFormMsg").textContent = e.message; });
  });

  $("btnPreview").addEventListener("click", function () {
    // Di browser: buka tab lebih dulu (sinkron dengan klik) agar tidak diblokir
    // pop-up blocker. Di aplikasi desktop setiap tab baru dibuka di browser bawaan,
    // jadi tab kosong tidak perlu disiapkan.
    var desktop = !!window.pywebview;
    var win = desktop ? null : window.open("", "_blank");
    if (win) win.document.write("<p style='font-family:sans-serif;padding:2rem'>Menyiapkan pratinjau PDF…</p>");
    $("invFormMsg").textContent = "";
    api("POST", "/api/invoices/preview", readInvoiceForm()).then(function (r) {
      if (win) win.location.href = r.url; else window.open(r.url, "_blank");
    }).catch(function (e) {
      if (win) win.close();
      $("invFormMsg").textContent = e.message;
    });
  });

  // -------------------------------------------------------------------------
  // Klien (dipakai bersama semua brand)
  // -------------------------------------------------------------------------
  function renderClients() {
    $("clientEmpty").classList.toggle("hidden", state.clients.length > 0);
    $("clientList").innerHTML = state.clients.map(function (c) {
      var count = state.invoices.filter(function (i) { return i.client_id === c.id; }).length;
      var contact = [c.phone, c.email].filter(Boolean).join(" · ");
      return '<div class="bg-white rounded-lg border border-slate-200 p-4" data-id="' + esc(c.id) + '">' +
        '<div class="flex items-start justify-between gap-2">' +
          '<div class="min-w-0"><div class="font-semibold text-slate-900">' + esc(c.name) + '</div>' +
          (c.address ? '<div class="text-sm text-slate-600 whitespace-pre-line break-words">' + esc(c.address) + '</div>' : "") +
          (contact ? '<div class="text-xs text-slate-500 mt-1 break-words">' + esc(contact) + '</div>' : "") +
          (c.npwp ? '<div class="text-xs text-slate-500">NPWP: ' + esc(c.npwp) + '</div>' : "") +
          '<div class="text-xs text-slate-500 mt-1">' + count + ' invoice</div></div>' +
          '<div class="flex gap-1 text-sm shrink-0">' +
            '<button type="button" data-act="inv" class="px-2 py-1 rounded border border-slate-300 hover:bg-slate-50" title="Buat invoice untuk klien ini" aria-label="Buat invoice untuk klien ini">' + DailyIcon("file-invoice") + '</button>' +
            '<button type="button" data-act="edit" class="inline-flex items-center gap-1 px-2 py-1 rounded border border-slate-300 hover:bg-slate-50" title="Edit" aria-label="Edit klien">' + DailyIcon("pencil") + '</button>' +
            '<button type="button" data-act="del" class="inline-flex items-center gap-1 px-2 py-1 rounded border border-slate-300 hover:bg-red-50 text-red-600" title="Hapus" aria-label="Hapus klien">' + DailyIcon("trash") + '</button>' +
          '</div></div></div>';
    }).join("");
  }

  function openClientForm(c) {
    $("k-id").value = c ? c.id : "";
    $("clientFormTitle").textContent = c ? "Edit klien" : "Klien baru";
    ["name", "address", "phone", "email", "npwp"].forEach(function (k) { $("k-" + k).value = c ? (c[k] || "") : ""; });
    $("clientFormMsg").textContent = "";
    $("clientForm").classList.remove("hidden");
    $("k-name").focus();
  }
  function closeClientForm() { $("clientForm").classList.add("hidden"); }

  $("btnNewClient").addEventListener("click", function () { openClientForm(null); });
  document.querySelectorAll(".js-client-cancel").forEach(function (b) { b.addEventListener("click", closeClientForm); });
  $("clientForm").addEventListener("submit", function (ev) {
    ev.preventDefault();
    var id = $("k-id").value;
    var data = {};
    ["name", "address", "phone", "email", "npwp"].forEach(function (k) { data[k] = $("k-" + k).value.trim(); });
    var req = id ? api("PUT", "/api/invoice/clients/" + id, data) : api("POST", "/api/invoice/clients", data);
    req.then(load).then(function () { closeClientForm(); toast("Klien disimpan"); })
      .catch(function (e) { $("clientFormMsg").textContent = e.message; });
  });
  $("clientList").addEventListener("click", function (ev) {
    var btn = ev.target.closest("button[data-act]");
    if (!btn) return;
    var id = btn.closest("[data-id]").dataset.id;
    var c = state.clients.find(function (x) { return x.id === id; });
    if (!c) return;
    if (btn.dataset.act === "edit") openClientForm(c);
    else if (btn.dataset.act === "inv") {
      openInvoiceForm(null);
      if (!state.brands.length) return;
      $("i-clientId").value = c.id;
      renderClientPick();
      setClientFields(c);
    } else if (btn.dataset.act === "del") {
      if (!confirm("Hapus klien " + c.name + "? Invoice yang sudah dibuat tidak ikut terhapus.")) return;
      api("DELETE", "/api/invoice/clients/" + id).then(load).then(function () { toast("Klien dihapus"); })
        .catch(function (e) { toast(e.message); });
    }
  });

  // -------------------------------------------------------------------------
  // Brand
  // -------------------------------------------------------------------------
  function renderBrands() {
    $("brandEmpty").classList.toggle("hidden", state.brands.length > 0);
    $("brandList").innerHTML = state.brands.map(function (b) {
      var contact = [b.phone, b.email].filter(Boolean).join(" · ");
      var design = DESIGN_BY_ID[b.design];
      var logo = b.has_logo
        ? '<img src="' + esc(logoUrl(b)) + '" alt="" class="max-w-full max-h-full object-contain">'
        : '<span class="text-2xl font-bold text-slate-500">' + esc(initial(b.name)) + '</span>';
      return '<div class="bg-white rounded-lg border ' + (b.is_default ? "border-amber-300" : "border-slate-200") + ' p-4" data-id="' + esc(b.id) + '">' +
        '<div class="flex items-start gap-3">' +
          '<div class="w-20 h-14 shrink-0 rounded-md border border-slate-200 bg-slate-50 flex items-center justify-center overflow-hidden p-1">' + logo + '</div>' +
          '<div class="min-w-0 flex-1">' +
            '<div class="flex flex-wrap items-center gap-2"><span class="font-semibold text-slate-900">' + esc(b.name) + '</span>' +
              (b.is_default ? '<span class="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full bg-blue-100 text-blue-800">' + DailyIcon("star") + ' Default</span>' : "") +
            '</div>' +
            (contact ? '<div class="text-xs text-slate-500 truncate">' + esc(contact) + '</div>' : "") +
            '<div class="text-xs text-slate-500 mt-1">Prefix <span class="font-mono">' + esc(b.prefix) + '</span> · ' +
              b.invoice_count + ' invoice' + (design ? ' · desain ' + esc(design.name) : "") + '</div>' +
          '</div></div>' +
        '<div class="flex flex-wrap gap-1 text-sm mt-3">' +
          '<button type="button" data-act="inv" class="inline-flex items-center gap-1 px-2 py-1 rounded border border-slate-300 hover:bg-slate-50">' + DailyIcon("file-invoice") + ' Buat invoice</button>' +
          '<button type="button" data-act="edit" class="inline-flex items-center gap-1 px-2 py-1 rounded border border-slate-300 hover:bg-slate-50">' + DailyIcon("pencil") + ' Edit</button>' +
          (b.is_default ? "" : '<button type="button" data-act="default" class="inline-flex items-center gap-1 px-2 py-1 rounded border border-slate-300 hover:bg-slate-50">' + DailyIcon("star") + ' Jadikan default</button>') +
        '</div></div>';
    }).join("");
  }

  $("brandList").addEventListener("click", function (ev) {
    var btn = ev.target.closest("button[data-act]");
    if (!btn) return;
    var b = BRAND_BY_ID[btn.closest("[data-id]").dataset.id];
    if (!b) return;
    if (btn.dataset.act === "edit") openBrandForm(b);
    else if (btn.dataset.act === "inv") openInvoiceForm(null, { brandId: b.id });
    else if (btn.dataset.act === "default") {
      api("POST", "/api/invoice/brands/" + b.id + "/default").then(load)
        .then(function () { toast(b.name + " kini brand default"); })
        .catch(function (e) { toast(e.message); });
    }
  });

  function bankRowHtml(bk) {
    bk = bk || {};
    return '<div class="grid grid-cols-1 sm:grid-cols-[1fr_1.4fr_1.6fr_auto] gap-2 js-bank">' +
      '<input class="inp js-bank-name" placeholder="Bank (mis. BCA)" value="' + esc(bk.bank) + '">' +
      '<input class="inp js-bank-number" placeholder="No. rekening" value="' + esc(bk.number) + '">' +
      '<input class="inp js-bank-holder" placeholder="Atas nama" value="' + esc(bk.holder) + '">' +
      '<button type="button" class="js-del-bank text-slate-500 hover:text-red-600 text-xl px-2" title="Hapus rekening">&times;</button></div>';
  }
  $("btnAddBank").addEventListener("click", function () {
    $("bankRows").insertAdjacentHTML("beforeend", bankRowHtml());
  });
  $("bankRows").addEventListener("click", function (ev) {
    if (ev.target.classList.contains("js-del-bank")) ev.target.closest(".js-bank").remove();
  });

  function updatePrefixExample() {
    var t = new Date();
    var prefix = ($("b-prefix").value || "INV").replace(/[\/\s]+/g, "");
    $("b-prefixEx").textContent = "001/" + prefix + "/" + ROMAWI[t.getMonth()] + "/" + t.getFullYear();
  }
  $("b-prefix").addEventListener("input", updatePrefixExample);

  function showBrandLogo(src) {
    $("logoImg").classList.toggle("hidden", !src);
    $("logoNone").classList.toggle("hidden", !!src);
    $("btnLogoDel").classList.toggle("hidden", !src);
    if (src) $("logoImg").src = src;
  }

  function pickBrandDesign(id) {
    brandDesign = id;
    $("b-designs").querySelectorAll(".design-card").forEach(function (c) {
      c.dataset.selected = String(c.dataset.id === id);
      c.setAttribute("aria-checked", String(c.dataset.id === id));
    });
    syncColorInput($("b-color"), $("b-colorWrap"), id, brandColor);
  }
  function renderBrandDesigns() {
    renderDesignGrid($("b-designs"), brandDesign, brandColor, pickBrandDesign, $("b-id").value);
    syncColorInput($("b-color"), $("b-colorWrap"), brandDesign, brandColor);
  }
  $("b-color").addEventListener("input", function () {
    brandColor = $("b-color").value;
    renderBrandDesigns();
  });
  $("btnBColorReset").addEventListener("click", function () { brandColor = ""; renderBrandDesigns(); });

  function setBrandMsg(text, ok) {
    $("brandMsg").className = "text-sm w-full " + (ok ? "text-green-700" : "text-red-700");
    $("brandMsg").textContent = text;
  }

  function openBrandForm(b) {
    $("b-id").value = b ? b.id : "";
    $("brandFormTitle").textContent = b ? "Edit brand: " + b.name : "Brand baru";
    ["name", "address", "phone", "email", "website", "npwp", "notes"].forEach(function (k) {
      $("b-" + k).value = b ? (b[k] || "") : "";
    });
    $("b-prefix").value = b ? b.prefix : "";
    $("b-due").value = b && b.due_days != null ? b.due_days : 14;
    $("b-tax").value = b && b.tax_rate != null ? b.tax_rate : 11;
    $("b-default").checked = b ? !!b.is_default : !state.brands.length;
    $("bankRows").innerHTML = (b && b.banks && b.banks.length ? b.banks : [null]).map(bankRowHtml).join("");
    brandDesign = (b && b.design) || (DESIGNS[0] && DESIGNS[0].id);
    brandColor = (b && b.accent_color) || "";
    renderBrandDesigns();
    updatePrefixExample();
    pendingLogo = null;
    showBrandLogo(b && b.has_logo ? logoUrl(b) : "");
    $("btnBrandDel").classList.toggle("hidden", !b);
    setBrandMsg("", true);
    $("brandListWrap").classList.add("hidden");
    $("brandForm").classList.remove("hidden");
    showTab("brands");
    window.scrollTo({ top: 0, behavior: "smooth" });
    $("b-name").focus();
  }
  function closeBrandForm() {
    $("brandForm").classList.add("hidden");
    $("brandListWrap").classList.remove("hidden");
    pendingLogo = null;
  }
  $("btnNewBrand").addEventListener("click", function () { openBrandForm(null); });
  document.querySelectorAll(".js-brand-cancel").forEach(function (b) { b.addEventListener("click", closeBrandForm); });

  function uploadLogo(brandId, file) {
    var fd = new FormData();
    fd.append("logo", file);
    return fetch("/api/invoice/brands/" + encodeURIComponent(brandId) + "/logo", { method: "POST", body: fd })
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (d) {
          if (!r.ok) throw new Error(d.error || "Gagal mengunggah logo.");
        });
      });
  }

  $("brandForm").addEventListener("submit", function (ev) {
    ev.preventDefault();
    var id = $("b-id").value;
    var data = {
      name: $("b-name").value, address: $("b-address").value, phone: $("b-phone").value,
      email: $("b-email").value, website: $("b-website").value, npwp: $("b-npwp").value,
      prefix: $("b-prefix").value, due_days: $("b-due").value, tax_rate: $("b-tax").value,
      notes: $("b-notes").value, design: brandDesign, accent_color: brandColor,
      is_default: $("b-default").checked,
      banks: Array.prototype.map.call($("bankRows").querySelectorAll(".js-bank"), function (row) {
        return {
          bank: row.querySelector(".js-bank-name").value,
          number: row.querySelector(".js-bank-number").value,
          holder: row.querySelector(".js-bank-holder").value
        };
      })
    };
    var req = id ? api("PUT", "/api/invoice/brands/" + id, data) : api("POST", "/api/invoice/brands", data);
    req.then(function (brand) {
      var next = pendingLogo ? uploadLogo(brand.id, pendingLogo) : Promise.resolve();
      return next.then(load).then(function () {
        closeBrandForm();
        toast("Brand " + brand.name + " disimpan");
      });
    }).catch(function (e) { setBrandMsg(e.message, false); });
  });

  $("logoFile").addEventListener("change", function () {
    var f = $("logoFile").files[0];
    $("logoFile").value = "";
    if (!f) return;
    var id = $("b-id").value;
    if (!id) {
      // Brand belum disimpan: tampilkan pratinjau, unggah setelah brand dibuat.
      pendingLogo = f;
      showBrandLogo(URL.createObjectURL(f));
      return;
    }
    uploadLogo(id, f).then(load).then(function () {
      showBrandLogo(logoUrl(BRAND_BY_ID[id]));
      toast("Logo diperbarui");
    }).catch(function (e) { setBrandMsg(e.message, false); });
  });
  $("btnLogoDel").addEventListener("click", function () {
    var id = $("b-id").value;
    if (!id) { pendingLogo = null; showBrandLogo(""); return; }
    if (!confirm("Hapus logo brand ini?")) return;
    api("DELETE", "/api/invoice/brands/" + id + "/logo").then(load).then(function () {
      showBrandLogo("");
      toast("Logo dihapus");
    }).catch(function (e) { setBrandMsg("Gagal menghapus logo: " + e.message, false); });
  });

  $("btnBrandDel").addEventListener("click", function () {
    var b = BRAND_BY_ID[$("b-id").value];
    if (!b) return;
    if (!confirm("Hapus brand " + b.name + " beserta logonya? Tindakan ini tidak bisa dibatalkan.")) return;
    api("DELETE", "/api/invoice/brands/" + b.id).then(load).then(function () {
      closeBrandForm();
      toast("Brand dihapus");
    }).catch(function (e) { setBrandMsg(e.message, false); });
  });

  // -------------------------------------------------------------------------
  // Mulai
  // -------------------------------------------------------------------------
  function start() {
    showLoadMessage("Memuat data invoice…");
    load().then(function () {
      var tab = "invoices";
      try { tab = sessionStorage.getItem("invoiceTab") || tab; } catch (e) { /* abaikan */ }
      if (!state.brands.length) tab = "brands";
      showTab(tab);
    }).catch(function () {
      showLoadMessage('Gagal memuat data invoice. Pastikan Daily App masih berjalan, lalu ' +
        '<button type="button" class="js-retry underline text-blue-700">coba lagi</button>.');
    });
  }
  document.addEventListener("click", function (ev) {
    if (ev.target.closest(".js-retry")) start();
  });
  start();
})();
