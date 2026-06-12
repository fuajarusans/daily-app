"""Engine inpainting LaMa (model ONNX) untuk tool Hapus Watermark.

Memakai onnxruntime yang SUDAH terpasang (lewat rembg) — TANPA torch. Model
`lama_fp32.onnx` (Carve/LaMa-ONNX, ~208 MB, Apache-2.0) diunduh SEKALI ke folder
`models/` saat pertama kali dipakai, lalu berjalan offline (pola seperti rembg).

Strategi: model menerima input tetap 512x512. Daripada mengecilkan seluruh gambar
(bikin hasil buram), kita potong (crop) area di sekitar watermark + margin konteks,
jalankan LaMa pada potongan itu, lalu tempel kembali dengan tepi di-blend (feather)
agar mulus dan detail di luar watermark tetap utuh.

Nama berkas diawali underscore '_' agar TIDAK ikut auto-import sebagai Tool.
"""
from __future__ import annotations

import os
import urllib.request
from pathlib import Path

import numpy as np

from app import config

MODEL_FILENAME = "lama_fp32.onnx"
MODEL_URL = "https://huggingface.co/Carve/LaMa-ONNX/resolve/main/lama_fp32.onnx"
MODEL_SIZE_MB = 208
INPUT_SIZE = 512

# Cache antar-request agar model hanya di-load sekali.
_session = None
_io_names: tuple[str, str, str] | None = None  # (image_input, mask_input, output)


def model_path() -> Path:
    return config.MODELS_DIR / MODEL_FILENAME


def onnxruntime_available() -> bool:
    try:
        import onnxruntime  # noqa: F401
        return True
    except ImportError:
        return False


def model_ready() -> bool:
    p = model_path()
    return p.exists() and p.stat().st_size > 1_000_000


def ensure_model() -> Path:
    """Pastikan berkas model ada; unduh bila belum. Kembalikan path-nya."""
    path = model_path()
    if model_ready():
        return path
    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    try:
        req = urllib.request.Request(MODEL_URL, headers={"User-Agent": "DailyApp/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp, open(tmp, "wb") as out:
            while True:
                chunk = resp.read(1024 * 256)
                if not chunk:
                    break
                out.write(chunk)
    except Exception as e:  # noqa: BLE001
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
        raise RuntimeError(
            f"Gagal mengunduh model LaMa (~{MODEL_SIZE_MB} MB): {e}. "
            "Pastikan ada koneksi internet pada pemakaian pertama."
        )
    os.replace(tmp, path)
    return path


def _get_session():
    global _session, _io_names
    if _session is not None:
        return _session
    import onnxruntime as ort

    path = ensure_model()
    sess = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])

    # Identifikasi input gambar (3 channel) vs mask (1 channel) lewat bentuknya,
    # agar tahan terhadap perbedaan penamaan antar-ekspor model.
    img_name = mask_name = None
    for inp in sess.get_inputs():
        ch = inp.shape[1] if len(inp.shape) == 4 else None
        if ch == 3:
            img_name = inp.name
        elif ch == 1:
            mask_name = inp.name
    if img_name is None or mask_name is None:
        names = [i.name for i in sess.get_inputs()]
        img_name, mask_name = names[0], names[1]
    out_name = sess.get_outputs()[0].name

    _io_names = (img_name, mask_name, out_name)
    _session = sess
    return _session


def _run_512(img_bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Jalankan LaMa pada satu potongan; kembalikan hasil BGR seukuran input."""
    import cv2

    sess = _get_session()
    img_name, mask_name, out_name = _io_names
    h, w = img_bgr.shape[:2]

    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    img_r = cv2.resize(img_rgb, (INPUT_SIZE, INPUT_SIZE), interpolation=cv2.INTER_AREA)
    img_t = (img_r.astype(np.float32) / 255.0).transpose(2, 0, 1)[None, ...]

    mask_r = cv2.resize(mask, (INPUT_SIZE, INPUT_SIZE), interpolation=cv2.INTER_NEAREST)
    mask_t = (mask_r > 127).astype(np.float32)[None, None, ...]  # 1.0 = inpaint

    out = sess.run([out_name], {img_name: img_t, mask_name: mask_t})[0]
    out = np.transpose(np.squeeze(out, 0), (1, 2, 0))  # [512,512,3] RGB
    if float(out.max()) <= 1.5:  # sebagian ekspor keluar 0..1, sebagian 0..255
        out = out * 255.0
    out = np.clip(out, 0, 255).astype(np.uint8)
    out_bgr = cv2.cvtColor(out, cv2.COLOR_RGB2BGR)
    return cv2.resize(out_bgr, (w, h), interpolation=cv2.INTER_CUBIC)


def inpaint(img_bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Inpaint dengan LaMa.

    Args:
        img_bgr: gambar HxWx3 (BGR, hasil cv2.imdecode).
        mask: HxW uint8 (0/255), 255 = area yang dihapus.
    Returns:
        Gambar BGR HxWx3, area termask diisi LaMa, tepi di-blend.
    """
    import cv2

    H, W = img_bgr.shape[:2]
    m = (mask > 127).astype(np.uint8)
    ys, xs = np.where(m > 0)
    if len(xs) == 0:
        return img_bgr

    # Kotak pembatas watermark + margin konteks untuk LaMa.
    x0, x1 = int(xs.min()), int(xs.max())
    y0, y1 = int(ys.min()), int(ys.max())
    bw, bh = x1 - x0 + 1, y1 - y0 + 1
    margin = int(max(bw, bh) * 0.6) + 16
    cx0, cy0 = max(0, x0 - margin), max(0, y0 - margin)
    cx1, cy1 = min(W, x1 + margin + 1), min(H, y1 + margin + 1)

    crop_img = img_bgr[cy0:cy1, cx0:cx1]
    crop_mask = (m[cy0:cy1, cx0:cx1] * 255).astype(np.uint8)

    filled = _run_512(crop_img, crop_mask)

    # Komposit feather: hanya area termask yang diganti, tepi mulus.
    soft = cv2.dilate(crop_mask, np.ones((3, 3), np.uint8), iterations=1)
    alpha = cv2.GaussianBlur(soft.astype(np.float32) / 255.0, (0, 0), sigmaX=2.0)
    alpha = np.clip(alpha, 0.0, 1.0)[..., None]
    blended = crop_img.astype(np.float32) * (1 - alpha) + filled.astype(np.float32) * alpha

    out = img_bgr.copy()
    out[cy0:cy1, cx0:cx1] = np.clip(blended, 0, 255).astype(np.uint8)
    return out
