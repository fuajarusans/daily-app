"""Route Invoice Generator: halaman `/invoice` + API (invoice, klien, brand, PDF).

Fitur stateful (data permanen di data/invoices.json), jadi BUKAN `Tool` — mengikuti
pola Catatan & Pengingat (`notes_routes.py`).
"""
from __future__ import annotations

import asyncio
import io
import re
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from starlette.datastructures import UploadFile

from app import config, invoice_store, utils
from app.invoice_designs import all_designs, get_design, render_pdf
from app.templating import templates

router = APIRouter()

MAX_LOGO_BYTES = 5 * 1024 * 1024


def _err(msg: str, status: int = 400) -> JSONResponse:
    return JSONResponse({"error": msg}, status_code=status)


def _designs() -> list[dict]:
    return [d.to_dict() for d in all_designs()]


def _pdf_filename(inv: dict) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]+", "-", inv.get("number") or "invoice").strip("-")
    return f"Invoice_{safe or 'baru'}.pdf"


async def _render(inv: dict, brand: Optional[dict] = None) -> bytes:
    brand = brand or invoice_store.get_brand(inv.get("brand_id") or "") or {}
    logo = invoice_store.logo_path(brand.get("id", ""))
    return await asyncio.to_thread(render_pdf, inv, brand, logo)


async def _pdf_response(inv: dict, download: bool, brand: Optional[dict] = None) -> Response:
    pdf = await _render(inv, brand)
    filename = _pdf_filename(inv)
    disposition = "attachment" if download else "inline"
    return Response(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'{disposition}; filename="{filename}"'},
    )


# ----------------------------------------------------------------------------
# Halaman
# ----------------------------------------------------------------------------
@router.get("/invoice", response_class=HTMLResponse)
async def invoice_page(request: Request):
    return templates.TemplateResponse(request, "invoice.html", {"designs": _designs()})


@router.get("/api/invoice/state")
async def api_state():
    return {
        "brands": invoice_store.list_brands(),
        "default_brand_id": invoice_store.default_brand_id(),
        "clients": invoice_store.list_clients(),
        "invoices": invoice_store.list_invoices(),
        "designs": _designs(),
    }


@router.get("/api/invoice/next-number")
async def api_next_number(date: str = "", brand_id: str = ""):
    return {"number": invoice_store.next_number(date or None, brand_id)}


# ----------------------------------------------------------------------------
# Invoice
# ----------------------------------------------------------------------------
@router.post("/api/invoices")
async def api_create(request: Request):
    inv, err = invoice_store.save_invoice(await request.json())
    return _err(err) if err else inv


@router.put("/api/invoices/{inv_id}")
async def api_update(inv_id: str, request: Request):
    inv, err = invoice_store.save_invoice(await request.json(), inv_id)
    return _err(err, 404 if err == "Invoice tidak ditemukan." else 400) if err else inv


@router.post("/api/invoices/{inv_id}/status")
async def api_status(inv_id: str, request: Request):
    data = await request.json()
    inv = invoice_store.set_status(inv_id, str(data.get("status") or ""))
    return inv if inv else _err("Invoice tidak ditemukan.", 404)


@router.post("/api/invoices/{inv_id}/duplicate")
async def api_duplicate(inv_id: str):
    inv = invoice_store.duplicate_invoice(inv_id)
    return inv if inv else _err("Invoice tidak ditemukan.", 404)


@router.delete("/api/invoices/{inv_id}")
async def api_delete(inv_id: str):
    if not invoice_store.delete_invoice(inv_id):
        return _err("Invoice tidak ditemukan.", 404)
    return {"ok": True}


@router.get("/api/invoices/{inv_id}/pdf")
async def api_pdf(inv_id: str, download: int = 0):
    inv = invoice_store.get_invoice(inv_id)
    if inv is None:
        return _err("Invoice tidak ditemukan.", 404)
    return await _pdf_response(inv, bool(download))


@router.post("/api/invoices/preview")
async def api_preview(request: Request):
    """Pratinjau PDF dari isi form yang belum disimpan.

    PDF disimpan sementara di storage/outputs (ikut auto-cleanup) dan yang dikirim
    balik adalah URL-nya, bukan isi PDF: URL biasa bisa dibuka di tab baru maupun di
    browser bawaan dari aplikasi desktop (blob: URL tidak bisa dibawa keluar jendela).
    """
    inv, err = invoice_store.build_preview(await request.json())
    if err:
        return _err(err)
    pdf = await _render(inv)
    job = utils.new_job_dir(config.OUTPUT_DIR)
    name = _pdf_filename(inv)
    (job / name).write_bytes(pdf)
    return {"url": f"/api/invoices/preview-file/{job.name}/{name}"}


@router.get("/api/invoices/preview-file/{job}/{filename}")
async def api_preview_file(job: str, filename: str):
    path = config.OUTPUT_DIR / utils.safe_filename(job) / utils.safe_filename(filename)
    if not path.is_file():
        return _err("Pratinjau sudah kedaluwarsa. Klik Pratinjau PDF lagi.", 404)
    return FileResponse(path, media_type="application/pdf", filename=path.name,
                        content_disposition_type="inline")


@router.get("/api/invoice/designs/{design_id}/sample.pdf")
async def api_design_sample(design_id: str, color: str = "", brand_id: str = ""):
    """Contoh PDF sebuah desain memakai data brand (bila ada) + data invoice contoh."""
    if get_design(design_id) is None:
        return _err("Desain tidak ditemukan.", 404)
    brand = invoice_store.get_brand(brand_id) if brand_id else None
    if brand is None:
        brand = invoice_store.get_brand("") or {"name": "Nama Brand Anda"}
    inv = invoice_store.sample_invoice(brand)
    inv["design"] = design_id
    inv["accent_color"] = color if re.fullmatch(r"#[0-9a-fA-F]{6}", color or "") else ""
    return await _pdf_response(inv, download=False, brand=brand)


# ----------------------------------------------------------------------------
# Klien
# ----------------------------------------------------------------------------
@router.post("/api/invoice/clients")
async def api_client_create(request: Request):
    data = await request.json()
    if not str(data.get("name") or "").strip():
        return _err("Nama klien wajib diisi.")
    return invoice_store.add_client(data)


@router.put("/api/invoice/clients/{client_id}")
async def api_client_update(client_id: str, request: Request):
    data = await request.json()
    if not str(data.get("name") or "").strip():
        return _err("Nama klien wajib diisi.")
    c = invoice_store.update_client(client_id, data)
    return c if c else _err("Klien tidak ditemukan.", 404)


@router.delete("/api/invoice/clients/{client_id}")
async def api_client_delete(client_id: str):
    if not invoice_store.delete_client(client_id):
        return _err("Klien tidak ditemukan.", 404)
    return {"ok": True}


# ----------------------------------------------------------------------------
# Brand (profil perusahaan) & logo per brand
# ----------------------------------------------------------------------------
@router.post("/api/invoice/brands")
async def api_brand_create(request: Request):
    brand, err = invoice_store.add_brand(await request.json())
    return _err(err) if err else brand


@router.put("/api/invoice/brands/{brand_id}")
async def api_brand_update(brand_id: str, request: Request):
    brand, err = invoice_store.update_brand(brand_id, await request.json())
    return _err(err, 404 if err == "Brand tidak ditemukan." else 400) if err else brand


@router.post("/api/invoice/brands/{brand_id}/default")
async def api_brand_default(brand_id: str):
    if not invoice_store.set_default_brand(brand_id):
        return _err("Brand tidak ditemukan.", 404)
    return {"ok": True}


@router.delete("/api/invoice/brands/{brand_id}")
async def api_brand_delete(brand_id: str):
    err = invoice_store.delete_brand(brand_id)
    return _err(err, 404 if err == "Brand tidak ditemukan." else 400) if err else {"ok": True}


@router.get("/api/invoice/brands/{brand_id}/logo")
async def api_logo_get(brand_id: str):
    path = invoice_store.logo_path(brand_id)
    if path is None:
        return _err("Logo belum diunggah.", 404)
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": "no-store"})


@router.post("/api/invoice/brands/{brand_id}/logo")
async def api_logo_upload(brand_id: str, request: Request):
    target = invoice_store.save_logo_target(brand_id)
    if target is None:
        return _err("Brand tidak ditemukan.", 404)
    form = await request.form()
    up = form.get("logo")
    if not isinstance(up, UploadFile):
        return _err("Pilih file gambar logo terlebih dahulu.")
    raw = await up.read()
    if len(raw) > MAX_LOGO_BYTES:
        return _err("Ukuran logo maksimal 5 MB.")

    def _save() -> None:
        from PIL import Image, ImageOps
        with Image.open(io.BytesIO(raw)) as im:
            im = ImageOps.exif_transpose(im)
            im.thumbnail((1200, 1200))
            im = im.convert("RGBA")
            config.ensure_dirs()
            im.save(target, "PNG")

    try:
        await asyncio.to_thread(_save)
    except Exception:  # noqa: BLE001
        return _err("File bukan gambar yang valid (gunakan PNG/JPG/WEBP).")
    return {"ok": True}


@router.delete("/api/invoice/brands/{brand_id}/logo")
async def api_logo_delete(brand_id: str):
    path = invoice_store.logo_path(brand_id)
    if path is not None:
        path.unlink(missing_ok=True)
    return {"ok": True}
