"""Entry point Daily App.

Jalankan dengan:  python run.py

Akan menyalakan server lokal dan otomatis membuka browser ke dashboard.
"""
import threading
import webbrowser

import uvicorn

from app import config


def _open_browser() -> None:
    """Buka browser ke dashboard setelah server sempat menyala."""
    url = f"http://localhost:{config.PORT}"
    webbrowser.open(url)


if __name__ == "__main__":
    config.ensure_dirs()

    # Buka browser sedikit setelah proses start (server butuh ~1 detik untuk siap).
    threading.Timer(1.5, _open_browser).start()

    print(f"\n  Daily App berjalan di http://localhost:{config.PORT}")
    print("  Tekan CTRL+C untuk berhenti.\n")

    uvicorn.run(
        "app.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=False,
    )
