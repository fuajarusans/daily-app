"""Entry point aplikasi desktop Daily App (dipakai untuk exe/installer).

Menyalakan server FastAPI (hanya 127.0.0.1), lalu membuka jendela aplikasi sendiri
(Edge WebView2 lewat pywebview, lihat app/desktop_shell.py). Menutup jendela utama =
aplikasi berhenti, kecuali masih ada sticky note di desktop (aplikasi tetap di tray).

Pemakaian:
    python desktop.py                      # jendela aplikasi
    python desktop.py --startup            # saat Windows menyala: pulihkan sticky saja
    python desktop.py --warmup             # siapkan profil LibreOffice (dipanggil installer)
    python desktop.py --server-only        # server saja (diagnosa / uji otomatis)
    python desktop.py --server-only --port 8020

Mode pengembang tetap `python run.py` (browser biasa, port 8000).
"""
from __future__ import annotations

import argparse
import logging
import socket
import sys
import threading
import time
import webbrowser
from logging.handlers import RotatingFileHandler

from app import config
from app.version import __version__

MUTEX_NAME = "DailyAppSingleInstance"  # sama dengan AppMutex di packaging/installer.iss
SHOW_EVENT_NAME = "DailyAppShowMain"   # sama dengan app/desktop_shell.py
WEBVIEW2_URL = "https://developer.microsoft.com/microsoft-edge/webview2/"
# Port tetap agar origin halaman sama tiap kali dibuka (localStorage: suara, notifikasi).
# Bila terpakai aplikasi lain, pakai port acak.
PREFERRED_PORT = 47815

log = logging.getLogger("dailyapp")


def _message_box(text: str, title: str = "Daily App") -> None:
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, text, title, 0x40)  # MB_ICONINFORMATION
    else:
        print(f"{title}: {text}")


def _already_running() -> bool:
    """Cegah dua salinan aplikasi berjalan bersamaan (data JSON yang sama)."""
    if sys.platform != "win32":
        return False
    import ctypes
    kernel32 = ctypes.windll.kernel32
    # Handle sengaja disimpan di modul agar mutex hidup selama proses berjalan.
    globals()["_mutex"] = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    return kernel32.GetLastError() == 183  # ERROR_ALREADY_EXISTS


def _create_show_event() -> None:
    """Buat event 'tampilkan jendela' sedini mungkin (sebelum server & jendela siap), agar
    permintaan dari peluncuran kedua tidak hilang. Event auto-reset: permintaan menunggu
    sampai app/desktop_shell.py mulai mendengarkan."""
    if sys.platform != "win32":
        return
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateEventW.restype = ctypes.c_void_p
    globals()["_show_event"] = kernel32.CreateEventW(None, False, False, SHOW_EVENT_NAME)


def _show_running_instance() -> bool:
    """Minta salinan yang sudah berjalan menampilkan jendela utamanya."""
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.OpenEventW.restype = ctypes.c_void_p
    handle = kernel32.OpenEventW(0x0002, False, SHOW_EVENT_NAME)  # EVENT_MODIFY_STATE
    if not handle:
        return False
    # Proses ini dibuka pengguna (boleh ke depan); izinkan salinan lama memajukan jendelanya.
    ctypes.windll.user32.AllowSetForegroundWindow(-1)  # ASFW_ANY
    kernel32.SetEvent(ctypes.c_void_p(handle))
    kernel32.CloseHandle(ctypes.c_void_p(handle))
    return True


def _setup_logging() -> None:
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(config.LOG_DIR / "daily-app.log", maxBytes=1_000_000,
                                  backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    if config.FROZEN:
        # Exe tanpa konsol: sys.stdout/stderr bernilai None dan akan membuat
        # uvicorn atau library lain gagal saat menulis log. Arahkan ke file.
        stream = open(config.LOG_DIR / "daily-app-console.log", "a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stdout or stream
        sys.stderr = sys.stderr or stream


def _free_port(preferred: int = 0) -> int:
    for port in ((preferred, 0) if preferred else (0,)):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((config.HOST, port))
            except OSError:
                continue
            return s.getsockname()[1]
    raise OSError("Tidak ada port lokal yang bisa dipakai")


def _start_server(port: int):
    import uvicorn
    from app.main import app

    server = uvicorn.Server(uvicorn.Config(app, host=config.HOST, port=port,
                                           log_level="warning", log_config=None))
    thread = threading.Thread(target=server.run, name="uvicorn", daemon=True)
    thread.start()
    deadline = time.time() + 20
    while not server.started:
        if not thread.is_alive() or time.time() > deadline:
            raise RuntimeError("Server lokal gagal menyala. Lihat log di " + str(config.LOG_DIR))
        time.sleep(0.05)
    return server, thread


def _open_window(url: str, startup: bool) -> bool:
    """Buka jendela aplikasi (dan sticky). False bila WebView2 tidak tersedia."""
    try:
        from app import desktop_shell
    except Exception:  # noqa: BLE001
        log.exception("pywebview tidak bisa dimuat")
        return False
    try:
        return desktop_shell.run(url, startup=startup)
    except Exception:  # noqa: BLE001
        log.exception("Gagal membuka jendela WebView2")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Daily App (aplikasi desktop)")
    parser.add_argument("--server-only", action="store_true", help="jalankan server tanpa jendela")
    parser.add_argument("--startup", action="store_true",
                        help="dijalankan saat Windows menyala: hanya memulihkan sticky note")
    parser.add_argument("--warmup", action="store_true",
                        help="siapkan profil LibreOffice lalu keluar (dipanggil installer)")
    parser.add_argument("--port", type=int, default=0, help="port server (default: tetap/acak)")
    args = parser.parse_args()

    if args.warmup:
        config.ensure_dirs()
        _setup_logging()
        from app import utils
        return 0 if utils.warm_libreoffice() else 1

    if not args.server_only:
        if _already_running():
            if args.startup:
                return 0
            if not _show_running_instance():
                _message_box("Daily App sudah berjalan. Cek jendela Daily App di taskbar atau ikon di tray.")
            return 0
        _create_show_event()

    config.ensure_dirs()
    _setup_logging()
    log.info("Daily App %s mulai (frozen=%s, data=%s, startup=%s)",
             __version__, config.FROZEN, config.USER_DIR, args.startup)

    if args.startup:
        from app import sticky_store
        if not sticky_store.restorable_ids():
            log.info("Mode startup: tidak ada sticky, keluar")
            return 0

    port = args.port or _free_port(0 if args.server_only else PREFERRED_PORT)
    try:
        server, thread = _start_server(port)
    except Exception as e:  # noqa: BLE001
        log.exception("Server gagal menyala")
        if args.server_only:
            # Mode diagnosa/uji: jangan memunculkan kotak pesan di layar pengguna.
            print(f"Daily App gagal dijalankan: {e}", file=sys.stderr, flush=True)
        else:
            _message_box(f"Daily App gagal dijalankan.\n\n{e}")
        return 1
    url = f"http://{config.HOST}:{port}/"
    log.info("Server aktif di %s", url)

    if not args.server_only:
        from app import utils
        if not utils.libreoffice_ready() and utils.find_libreoffice():
            # Profil belum siap (mis. pemanasan saat instal dilewati): siapkan di latar.
            threading.Thread(target=utils.warm_libreoffice, name="lo-warmup", daemon=True).start()

    if args.server_only:
        print(f"Daily App {__version__} berjalan di {url} (CTRL+C untuk berhenti)", flush=True)
        try:
            while thread.is_alive():
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
    elif not _open_window(url, args.startup):
        # Cadangan: tanpa WebView2, pakai browser bawaan selama kotak pesan terbuka.
        webbrowser.open(url)
        _message_box(
            "Jendela aplikasi tidak bisa dibuka karena Microsoft Edge WebView2 Runtime "
            f"belum terpasang (unduh gratis: {WEBVIEW2_URL}).\n\n"
            "Untuk sementara Daily App dibuka di browser. Biarkan kotak ini terbuka "
            "selama memakai aplikasi; klik OK untuk menutup Daily App."
        )

    server.should_exit = True
    thread.join(timeout=5)
    log.info("Daily App berhenti")
    return 0


if __name__ == "__main__":
    sys.exit(main())
