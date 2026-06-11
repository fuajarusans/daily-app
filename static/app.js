// Logika frontend untuk halaman tool: submit form, tampilkan status & hasil.
(function () {
    const form = document.getElementById("tool-form");
    if (!form) return;

    const statusBox = document.getElementById("status");
    const resultBox = document.getElementById("result");
    const submitBtn = document.getElementById("submit-btn");
    const toolId = form.dataset.toolId;
    const requiresFile = form.dataset.requiresFile === "true";

    function show(el, html, classes) {
        el.className = "mt-6 rounded-md p-4 text-sm " + classes;
        el.innerHTML = html;
        el.classList.remove("hidden");
    }

    function showStatus(html, classes) {
        show(statusBox, html, classes);
    }

    function clearResult() {
        resultBox.classList.add("hidden");
        resultBox.innerHTML = "";
    }

    form.addEventListener("submit", async function (e) {
        e.preventDefault();
        clearResult();

        const fileInput = form.querySelector('input[type="file"]');
        if (requiresFile && (!fileInput || fileInput.files.length === 0)) {
            showStatus("Silakan pilih file terlebih dahulu.",
                "bg-amber-50 border border-amber-200 text-amber-800");
            return;
        }

        const formData = new FormData(form);

        submitBtn.disabled = true;
        submitBtn.textContent = "Memproses…";
        showStatus(
            '<div class="flex items-center gap-2"><span class="animate-spin">⏳</span> Sedang memproses, mohon tunggu…</div>',
            "bg-blue-50 border border-blue-200 text-blue-800"
        );

        try {
            const resp = await fetch(`/api/tool/${toolId}/process`, {
                method: "POST",
                body: formData,
            });
            const data = await resp.json();

            if (!resp.ok) {
                showStatus("❌ " + (data.error || "Terjadi kesalahan."),
                    "bg-red-50 border border-red-200 text-red-800");
            } else {
                showStatus("✅ Berhasil diproses.",
                    "bg-green-50 border border-green-200 text-green-800");
                show(resultBox,
                    `<a href="${data.download_url}" download
                        class="inline-flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white font-medium px-5 py-2.5 rounded-md">
                        ⬇️ Unduh hasil (${data.filename})
                     </a>`,
                    "");
            }
        } catch (err) {
            showStatus("❌ Tidak dapat terhubung ke server: " + err.message,
                "bg-red-50 border border-red-200 text-red-800");
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = "Proses";
        }
    });
})();
