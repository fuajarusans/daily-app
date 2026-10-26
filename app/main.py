"""Aplikasi FastAPI utama: dashboard, halaman tool generik, proses, dan download."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
# request.form() menghasilkan starlette.datastructures.UploadFile; fastapi.UploadFile
# adalah subclass-nya, jadi cek isinstance harus pakai kelas Starlette agar cocok.
from starlette.datastructures import UploadFile
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app import cleanup, config, invoice_routes, notes_routes, utils, watermark_routes
from app.registry import ToolError, all_tools, get_tool
from app.templating import templates

# Mengimpor paket `tools` akan otomatis memuat & mendaftarkan semua tool.
import tools  # noqa: F401  (import untuk efek samping: registrasi tool)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    config.ensure_dirs()
    cleanup.purge_old_files()
    task = asyncio.create_task(cleanup.cleanup_loop())
    yield
    # Shutdown
    task.cancel()


app = FastAPI(title="Daily App", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")

# Server lokal tanpa login di port tetap: tolak permintaan yang Host-nya bukan komputer ini
# (serangan DNS rebinding dari situs lain di browser).
_LOCAL_HOSTS = {"127.0.0.1", "localhost"}
app.add_middleware(TrustedHostMiddleware, allowed_hosts=sorted(_LOCAL_HOSTS))


@app.middleware("http")
async def local_only_and_fresh(request: Request, call_next):
    # Situs lain di browser tidak boleh mengubah data (POST/PUT/DELETE lintas origin).
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        origin = request.headers.get("origin")
        if origin and urlsplit(origin).hostname not in _LOCAL_HOSTS:
            return JSONResponse({"error": "Permintaan ditolak."}, status_code=403)
    response = await call_next(request)
    # Port aplikasi kini tetap, jadi cache WebView2 bertahan antarversi: minta browser
    # selalu memvalidasi berkas statis (ETag) agar versi baru langsung terpakai.
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache"
    return response

# Fitur Catatan & Pengingat (halaman + API CRUD)
app.include_router(notes_routes.router)

# Halaman kustom "Hapus Watermark" (editor kanvas). Proses tetap lewat endpoint
# tool standar /api/tool/watermark-remove/process.
app.include_router(watermark_routes.router)

# Invoice Generator (halaman + API; data permanen di data/invoices.json)
app.include_router(invoice_routes.router)


# ----------------------------------------------------------------------------
# Halaman HTML
# ----------------------------------------------------------------------------
def _format_chips(exts: list[str]) -> str:
    """['.png', '.jpg', '.jpeg', ...] → 'PNG · JPG · +5' (format masukan, ringkas)."""
    names: list[str] = []
    for e in exts:
        n = e.lstrip(".").upper().replace("JPEG", "JPG")
        if n not in names:
            names.append(n)
    shown = " · ".join(names[:3])
    return shown + (f" · +{len(names) - 3}" if len(names) > 3 else "")


def _home_tiles() -> list[dict[str, Any]]:
    """Isi rail Beranda: Catatan, Invoice, lalu semua tool terdaftar."""
    tiles: list[dict[str, Any]] = [
        {"id": "notes", "href": "/notes", "title": "Catatan & Pengingat", "glyph": "notes",
         "desc": "Catatan, tugas, dan pengingat jatuh tempo, lengkap dengan kategori dan tag.",
         "chips": ["Tersimpan permanen"], "ready": True, "badge": True, "hue": "#e09f3e"},
        {"id": "invoice", "href": "/invoice", "title": "Invoice Generator", "glyph": "file-invoice",
         "desc": "Invoice PDF untuk beberapa brand: nomor otomatis, klien tersimpan, 10 desain.",
         "chips": ["PDF", "Multi-brand"], "ready": True, "hue": "#3fa66b"},
    ]
    for t in all_tools():
        d = t.to_dict()
        chips = [_format_chips(d["accepted_extensions"])] if d["accepted_extensions"] else ["Tanpa file"]
        if d["supports_batch"]:
            chips.append("Banyak file sekaligus")
        tiles.append({"id": d["id"], "href": d["custom_url"] or f"/tool/{d['id']}", "title": d["name"],
                      "glyph": d["glyph"], "hue": d["hue"], "desc": d["description"], "chips": chips,
                      "ready": d["ready"], "dep_message": d["dependency_message"]})
    return tiles


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(
        request, "dashboard.html", {"tiles": _home_tiles(), "tool_count": len(all_tools())}
    )


@app.get("/tool/{tool_id}", response_class=HTMLResponse)
async def tool_page(request: Request, tool_id: str):
    tool = get_tool(tool_id)
    if tool is None:
        return HTMLResponse("<h1>Tool tidak ditemukan</h1>", status_code=404)
    return templates.TemplateResponse(
        request, "tool.html", {"tool": tool.to_dict()}
    )


# ----------------------------------------------------------------------------
# API proses
# ----------------------------------------------------------------------------
def _coerce_option(raw: Any, spec: dict[str, Any]) -> Any:
    """Konversi nilai opsi dari form (string) ke tipe yang sesuai spesifikasi."""
    opt_type = spec.get("type", "text")
    # Checkbox: bila tidak dicentang, field tidak terkirim (raw=None) -> False.
    if opt_type == "checkbox":
        if raw is None:
            return False
        return str(raw).lower() in ("1", "true", "on", "yes")
    if raw is None or raw == "":
        return spec.get("default")
    try:
        if opt_type in ("number", "range"):
            # Bila ada step desimal, perlakukan sebagai float
            if isinstance(spec.get("step"), float) or "." in str(raw):
                return float(raw)
            return int(raw)
    except (TypeError, ValueError):
        return spec.get("default")
    return raw


def _too_big_message() -> str:
    limit = config.MAX_UPLOAD_BYTES
    size = f"{limit // (1024 * 1024)} MB" if limit >= 1024 * 1024 else f"{limit // 1024} KB"
    return f"Ukuran upload melebihi batas {size} per proses. Kurangi jumlah atau ukuran file."


@app.post("/api/tool/{tool_id}/process")
async def process_tool(tool_id: str, request: Request):
    tool = get_tool(tool_id)
    if tool is None:
        return JSONResponse({"error": "Tool tidak ditemukan."}, status_code=404)

    dep_msg = tool.check_dependencies()
    if dep_msg is not None:
        return JSONResponse({"error": dep_msg}, status_code=400)

    too_big = _too_big_message()
    length = request.headers.get("content-length", "")
    if length.isdigit() and int(length) > config.MAX_UPLOAD_BYTES:
        return JSONResponse({"error": too_big}, status_code=413)

    form = await request.form()

    # Kumpulkan file upload
    uploads: list[UploadFile] = []
    for value in form.getlist("files"):
        if isinstance(value, UploadFile):
            uploads.append(value)

    if tool.requires_file and not uploads:
        return JSONResponse(
            {"error": "Silakan pilih minimal satu file terlebih dahulu."},
            status_code=400,
        )

    # Validasi ekstensi
    if tool.accepted_extensions:
        accepted = {e.lower() for e in tool.accepted_extensions}
        for up in uploads:
            ext = Path(up.filename or "").suffix.lower()
            if ext not in accepted:
                return JSONResponse(
                    {
                        "error": f"Format '{ext or 'tidak dikenal'}' tidak didukung. "
                        f"Format yang diterima: {', '.join(sorted(accepted))}."
                    },
                    status_code=400,
                )

    # Kumpulkan & konversi opsi
    options: dict[str, Any] = {}
    for spec in tool.options:
        name = spec["name"]
        options[name] = _coerce_option(form.get(name), spec)

    # Siapkan folder kerja
    config.ensure_dirs()
    input_dir = utils.new_job_dir(config.UPLOAD_DIR)
    output_dir = utils.new_job_dir(config.OUTPUT_DIR)

    input_paths = await utils.save_uploads(uploads, input_dir) if uploads else []
    # Content-Length bisa absen (chunked), jadi ukur juga hasil simpanan.
    if sum(p.stat().st_size for p in input_paths) > config.MAX_UPLOAD_BYTES:
        for p in input_paths:
            p.unlink(missing_ok=True)
        return JSONResponse({"error": too_big}, status_code=413)

    # Jalankan proses (di thread agar tidak memblokir event loop)
    try:
        results = await asyncio.to_thread(
            tool.process, input_paths, options, output_dir
        )
    except ToolError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:  # noqa: BLE001
        return JSONResponse(
            {"error": f"Terjadi kesalahan saat memproses: {e}"}, status_code=500
        )

    if not results:
        return JSONResponse(
            {"error": "Proses selesai tetapi tidak menghasilkan file."},
            status_code=500,
        )

    # Bungkus jadi zip bila hasil lebih dari satu file
    if len(results) > 1:
        zip_name = f"{tool.id}_hasil.zip"
        final = utils.make_zip(results, output_dir, zip_name)
    else:
        final = results[0]

    download_url = f"/download/{output_dir.name}/{final.name}"
    return JSONResponse({"download_url": download_url, "filename": final.name})


# ----------------------------------------------------------------------------
# Download file hasil
# ----------------------------------------------------------------------------
@app.get("/download/{job}/{filename}")
async def download(job: str, filename: str):
    # Cegah path traversal: pakai hanya nama dasar
    safe_job = utils.safe_filename(job)
    safe_name = utils.safe_filename(filename)
    path = config.OUTPUT_DIR / safe_job / safe_name
    if not path.exists() or not path.is_file():
        return JSONResponse({"error": "File tidak ditemukan atau sudah dibersihkan."}, status_code=404)
    return FileResponse(path, filename=safe_name)
