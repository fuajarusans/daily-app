// Editor kanvas untuk tool "Hapus Watermark".
// Alur: muat gambar -> sapukan kuas/kotak menutupi watermark (overlay merah) ->
// ekspor mask hitam-putih (PNG) -> kirim gambar + mask ke endpoint tool standar.
(function () {
    "use strict";

    const TOOL_ID = "watermark-remove";
    const MASK_ALPHA_THRESHOLD = 25; // piksel overlay dengan alpha di atas ini = ditandai
    const MAX_UNDO = 20;

    const fileInput = document.getElementById("wm-file");
    if (!fileInput) return;

    const editor = document.getElementById("wm-editor");
    const wrap = document.getElementById("wm-canvas-wrap");
    const imgCanvas = document.getElementById("wm-img-canvas");
    const maskCanvas = document.getElementById("wm-mask-canvas");
    const imgCtx = imgCanvas.getContext("2d");
    const maskCtx = maskCanvas.getContext("2d", { willReadFrequently: true });

    const sizeInput = document.getElementById("wm-brush-size");
    const sizeVal = document.getElementById("wm-brush-size-val");
    const undoBtn = document.getElementById("wm-undo");
    const clearBtn = document.getElementById("wm-clear");
    const engineSel = document.getElementById("wm-engine");
    const lamaNote = document.getElementById("wm-lama-note");
    const opencvOpts = document.getElementById("wm-opencv-opts");
    const methodSel = document.getElementById("wm-method");
    const radiusInput = document.getElementById("wm-radius");
    const processBtn = document.getElementById("wm-process");
    const statusBox = document.getElementById("wm-status");
    const resultBox = document.getElementById("wm-result");
    const modeButtons = Array.prototype.slice.call(document.querySelectorAll(".wm-mode"));

    // --- State ---
    let imageFile = null;       // File asli yang diunggah (dikirim apa adanya)
    let mode = "brush";         // "brush" | "rect" | "eraser"
    let drawing = false;
    let lastPt = null;          // titik terakhir (koordinat kanvas) untuk kuas
    let rectStart = null;       // titik awal kotak
    let preDragSnapshot = null; // ImageData sebelum drag kotak (untuk preview)
    const undoStack = [];

    // --- Util tampilan ---
    function show(el, html, classes) {
        el.className = "mt-6 rounded-md p-4 text-sm " + classes;
        el.innerHTML = html;
        el.classList.remove("hidden");
    }
    function showStatus(html, classes) { show(statusBox, html, classes); }
    function clearResult() { resultBox.classList.add("hidden"); resultBox.innerHTML = ""; }

    // --- Muat gambar ---
    fileInput.addEventListener("change", async function () {
        const file = fileInput.files && fileInput.files[0];
        if (!file) return;
        imageFile = file;
        clearResult();
        statusBox.classList.add("hidden");

        let bitmap;
        try {
            // imageOrientation:'none' -> JANGAN putar berdasar EXIF, agar piksel
            // sama persis dengan yang dibaca OpenCV di backend (mask tetap sejajar).
            bitmap = await createImageBitmap(file, { imageOrientation: "none" });
        } catch (err) {
            // Fallback browser lama: pakai <img> (mungkin menerapkan orientasi EXIF).
            bitmap = await loadViaImg(file);
        }

        imgCanvas.width = bitmap.width;
        imgCanvas.height = bitmap.height;
        maskCanvas.width = bitmap.width;
        maskCanvas.height = bitmap.height;
        imgCtx.clearRect(0, 0, imgCanvas.width, imgCanvas.height);
        imgCtx.drawImage(bitmap, 0, 0);
        if (bitmap.close) bitmap.close();

        maskCtx.clearRect(0, 0, maskCanvas.width, maskCanvas.height);
        undoStack.length = 0;
        editor.classList.remove("hidden");
    });

    function loadViaImg(file) {
        return new Promise(function (resolve, reject) {
            const url = URL.createObjectURL(file);
            const im = new Image();
            im.onload = function () { URL.revokeObjectURL(url); resolve(im); };
            im.onerror = function () { URL.revokeObjectURL(url); reject(new Error("gagal memuat gambar")); };
            im.src = url;
        });
    }

    // --- Pemetaan koordinat layar -> piksel kanvas ---
    function toCanvasPt(e) {
        const r = maskCanvas.getBoundingClientRect();
        const sx = maskCanvas.width / r.width;
        const sy = maskCanvas.height / r.height;
        return { x: (e.clientX - r.left) * sx, y: (e.clientY - r.top) * sy };
    }
    // Ukuran kuas mengikuti tampilan (piksel layar) lalu diskalakan ke piksel kanvas,
    // sehingga terasa konsisten berapa pun resolusi gambar.
    function brushPx() {
        const r = maskCanvas.getBoundingClientRect();
        const sx = maskCanvas.width / (r.width || 1);
        return Math.max(1, parseInt(sizeInput.value, 10) * sx);
    }

    function pushUndo() {
        try {
            undoStack.push(maskCtx.getImageData(0, 0, maskCanvas.width, maskCanvas.height));
            if (undoStack.length > MAX_UNDO) undoStack.shift();
        } catch (e) { /* abaikan bila gambar terlalu besar */ }
    }

    function setStroke(erase) {
        maskCtx.globalCompositeOperation = erase ? "destination-out" : "source-over";
        maskCtx.strokeStyle = "rgba(239,68,68,0.65)";
        maskCtx.fillStyle = "rgba(239,68,68,0.65)";
        maskCtx.lineWidth = brushPx();
        maskCtx.lineCap = "round";
        maskCtx.lineJoin = "round";
    }

    function dot(pt, erase) {
        setStroke(erase);
        maskCtx.beginPath();
        maskCtx.arc(pt.x, pt.y, brushPx() / 2, 0, Math.PI * 2);
        maskCtx.fill();
    }
    function lineTo(pt, erase) {
        setStroke(erase);
        maskCtx.beginPath();
        maskCtx.moveTo(lastPt.x, lastPt.y);
        maskCtx.lineTo(pt.x, pt.y);
        maskCtx.stroke();
    }

    // --- Event menggambar (pointer = mouse + sentuh) ---
    maskCanvas.addEventListener("pointerdown", function (e) {
        if (!imageFile) return;
        e.preventDefault();
        maskCanvas.setPointerCapture(e.pointerId);
        drawing = true;
        pushUndo();
        const pt = toCanvasPt(e);
        if (mode === "rect") {
            rectStart = pt;
            preDragSnapshot = maskCtx.getImageData(0, 0, maskCanvas.width, maskCanvas.height);
        } else {
            lastPt = pt;
            dot(pt, mode === "eraser");
        }
    });

    maskCanvas.addEventListener("pointermove", function (e) {
        if (!drawing) return;
        e.preventDefault();
        const pt = toCanvasPt(e);
        if (mode === "rect") {
            maskCtx.putImageData(preDragSnapshot, 0, 0);
            drawRect(rectStart, pt);
        } else {
            lineTo(pt, mode === "eraser");
            lastPt = pt;
        }
    });

    function endStroke(e) {
        if (!drawing) return;
        drawing = false;
        if (mode === "rect" && rectStart) {
            const pt = toCanvasPt(e);
            maskCtx.putImageData(preDragSnapshot, 0, 0);
            drawRect(rectStart, pt);
            rectStart = null;
            preDragSnapshot = null;
        }
        maskCtx.globalCompositeOperation = "source-over";
    }
    maskCanvas.addEventListener("pointerup", endStroke);
    maskCanvas.addEventListener("pointercancel", endStroke);

    function drawRect(a, b) {
        const x = Math.min(a.x, b.x), y = Math.min(a.y, b.y);
        const w = Math.abs(a.x - b.x), h = Math.abs(a.y - b.y);
        maskCtx.globalCompositeOperation = "source-over";
        maskCtx.fillStyle = "rgba(239,68,68,0.65)";
        maskCtx.fillRect(x, y, w, h);
    }

    // --- Toolbar ---
    modeButtons.forEach(function (btn) {
        btn.addEventListener("click", function () {
            mode = btn.dataset.mode;
            modeButtons.forEach(function (b) {
                const active = b === btn;
                b.classList.toggle("bg-blue-600", active);
                b.classList.toggle("text-white", active);
                b.classList.toggle("bg-white", !active);
                b.classList.toggle("text-slate-700", !active);
            });
        });
    });

    sizeInput.addEventListener("input", function () { sizeVal.textContent = sizeInput.value; });

    // Engine: opsi Telea/radius hanya relevan untuk OpenCV.
    engineSel.addEventListener("change", function () {
        const lama = engineSel.value === "lama";
        lamaNote.classList.toggle("hidden", !lama);
        opencvOpts.classList.toggle("hidden", lama);
    });

    undoBtn.addEventListener("click", function () {
        const snap = undoStack.pop();
        if (snap) maskCtx.putImageData(snap, 0, 0);
    });

    clearBtn.addEventListener("click", function () {
        if (!imageFile) return;
        pushUndo();
        maskCtx.clearRect(0, 0, maskCanvas.width, maskCanvas.height);
    });

    // --- Bangun mask hitam-putih untuk dikirim ke backend ---
    function buildMaskBlob() {
        return new Promise(function (resolve, reject) {
            const w = maskCanvas.width, h = maskCanvas.height;
            const src = maskCtx.getImageData(0, 0, w, h).data;
            const out = maskCtx.createImageData(w, h);
            const d = out.data;
            let marked = 0;
            for (let i = 0; i < src.length; i += 4) {
                const on = src[i + 3] > MASK_ALPHA_THRESHOLD; // alpha overlay
                const v = on ? 255 : 0;
                if (on) marked++;
                d[i] = v; d[i + 1] = v; d[i + 2] = v; d[i + 3] = 255;
            }
            if (marked === 0) { resolve(null); return; }
            const off = document.createElement("canvas");
            off.width = w; off.height = h;
            off.getContext("2d").putImageData(out, 0, 0);
            off.toBlob(function (blob) {
                blob ? resolve(blob) : reject(new Error("gagal membuat mask"));
            }, "image/png");
        });
    }

    // --- Proses ---
    processBtn.addEventListener("click", async function () {
        if (!imageFile) return;
        clearResult();

        let maskBlob;
        try {
            maskBlob = await buildMaskBlob();
        } catch (err) {
            showStatus("❌ Gagal menyiapkan mask: " + err.message,
                "bg-red-50 border border-red-200 text-red-800");
            return;
        }
        if (!maskBlob) {
            showStatus("Area watermark belum ditandai. Sapukan kuas di atas watermark dulu.",
                "bg-amber-50 border border-amber-200 text-amber-800");
            return;
        }

        const fd = new FormData();
        fd.append("files", imageFile, imageFile.name);      // gambar (urutan ke-1)
        fd.append("files", maskBlob, "mask.png");           // mask (urutan ke-2)
        fd.append("engine", engineSel.value);
        fd.append("method", methodSel.value);
        fd.append("radius", radiusInput.value);

        processBtn.disabled = true;
        processBtn.textContent = "Memproses…";
        const lama = engineSel.value === "lama";
        const wait = lama
            ? "Memproses dengan LaMa… (pemakaian pertama mengunduh model ~208 MB, bisa beberapa menit)"
            : "Sedang memproses…";
        showStatus('<div class="flex items-center gap-2"><span class="animate-spin">⏳</span> ' + wait + "</div>",
            "bg-blue-50 border border-blue-200 text-blue-800");

        try {
            const resp = await fetch(`/api/tool/${TOOL_ID}/process`, { method: "POST", body: fd });
            const data = await resp.json();
            if (!resp.ok) {
                showStatus("❌ " + (data.error || "Terjadi kesalahan."),
                    "bg-red-50 border border-red-200 text-red-800");
            } else {
                showStatus("✅ Berhasil diproses.",
                    "bg-green-50 border border-green-200 text-green-800");
                showResult(data);
            }
        } catch (err) {
            showStatus("❌ Tidak dapat terhubung ke server: " + err.message,
                "bg-red-50 border border-red-200 text-red-800");
        } finally {
            processBtn.disabled = false;
            processBtn.textContent = "3. Proses";
        }
    });

    function showResult(data) {
        const beforeUrl = URL.createObjectURL(imageFile);
        show(resultBox,
            `<div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
                <div>
                    <p class="text-xs font-medium text-slate-500 mb-1">Sebelum</p>
                    <img src="${beforeUrl}" class="w-full rounded-md border border-slate-200">
                </div>
                <div>
                    <p class="text-xs font-medium text-slate-500 mb-1">Sesudah</p>
                    <img src="${data.download_url}" class="w-full rounded-md border border-slate-200">
                </div>
             </div>
             <a href="${data.download_url}" download
                class="inline-flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white font-medium px-5 py-2.5 rounded-md">
                ⬇️ Unduh hasil (${data.filename})
             </a>`,
            "");
    }
})();
