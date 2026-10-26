"""Jendela desktop Daily App: jendela utama, sticky note, ikon tray, dan single-instance.

Hanya dipakai oleh desktop.py (Windows + pywebview/WebView2). Semua koordinat dalam
piksel logis (seperti pywebview): piksel fisik dibagi skala DPI sistem.

Perilaku:
- Sticky = jendela kecil tanpa bingkai yang memuat /sticky/<id>. Tidak tampil di taskbar.
- Menutup jendela utama saat masih ada sticky: aplikasi tetap jalan (ikon tray), dan
  jendela utama dibuat ulang saat dibuka lagi. Tanpa sticky, menutup jendela = keluar.
- Status sticky (terbuka, posisi, ukuran) disimpan di data/stickies.json, lalu dipulihkan
  saat aplikasi dibuka lagi atau saat Windows menyala (mode --startup).
"""
from __future__ import annotations

import ctypes
import logging
import threading
import time
from ctypes import wintypes
from typing import Optional
from urllib.parse import urlsplit

import webview

from app import config, notes_store, sticky_store
from app.version import __version__

log = logging.getLogger("dailyapp.desktop")

SHOW_EVENT_NAME = "DailyAppShowMain"   # sama dengan desktop.py; dipicu oleh salinan kedua
STICKY_TITLE = "Sticky · Daily App"
_COLOR_BG = {c[0]: c[2] for c in config.STICKY_COLORS}

# --- Win32 ---------------------------------------------------------------------------
# Instance DLL sendiri: argtypes yang dipasang di bawah tidak boleh mengubah fungsi
# ctypes.windll.user32 yang juga dipakai pywebview (objek fungsinya dipakai bersama).
_user32 = ctypes.WinDLL("user32", use_last_error=True)
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x80
WS_EX_APPWINDOW = 0x40000
SM_SWAPBUTTON = 23
SM_SHUTTINGDOWN = 0x2000
VK_LBUTTON, VK_RBUTTON = 0x01, 0x02
MONITOR_DEFAULTTONULL, MONITOR_DEFAULTTOPRIMARY, MONITOR_DEFAULTTONEAREST = 0, 1, 2
SWP_NOMOVE, SWP_NOZORDER, SWP_NOACTIVATE = 0x0002, 0x0004, 0x0010
INFINITE = 0xFFFFFFFF


class _MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]


_user32.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
_user32.MonitorFromPoint.restype = ctypes.c_void_p
_user32.MonitorFromRect.argtypes = [ctypes.POINTER(wintypes.RECT), wintypes.DWORD]
_user32.MonitorFromRect.restype = ctypes.c_void_p
_user32.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.POINTER(_MONITORINFO)]
_user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
_user32.GetWindowLongW.restype = wintypes.LONG
_user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.LONG]
_user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                 ctypes.c_int, ctypes.c_int, wintypes.UINT]
_user32.GetDpiForWindow.argtypes = [wintypes.HWND]
_user32.GetDpiForWindow.restype = wintypes.UINT
_kernel32.CreateEventW.restype = ctypes.c_void_p
_kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, wintypes.DWORD]


def _scale() -> float:
    try:
        return _user32.GetDpiForSystem() / 96.0
    except AttributeError:  # Windows lama
        return 1.0


def _cursor() -> tuple[float, float]:
    pt = wintypes.POINT()
    _user32.GetCursorPos(ctypes.byref(pt))
    s = _scale()
    return pt.x / s, pt.y / s


def _mouse_down() -> bool:
    vk = VK_RBUTTON if _user32.GetSystemMetrics(SM_SWAPBUTTON) else VK_LBUTTON
    return bool(_user32.GetAsyncKeyState(vk) & 0x8000)


def _shutting_down() -> bool:
    return bool(_user32.GetSystemMetrics(SM_SHUTTINGDOWN))


def _work_area(x: Optional[float] = None, y: Optional[float] = None) -> tuple[float, float, float, float]:
    """Area kerja (tanpa taskbar) monitor yang memuat titik (x, y), atau monitor utama."""
    s = _scale()
    if x is None or y is None:
        mon = _user32.MonitorFromPoint(wintypes.POINT(0, 0), MONITOR_DEFAULTTOPRIMARY)
    else:
        mon = _user32.MonitorFromPoint(wintypes.POINT(int(x * s), int(y * s)), MONITOR_DEFAULTTONEAREST)
    info = _MONITORINFO()
    info.cbSize = ctypes.sizeof(_MONITORINFO)
    if not mon or not _user32.GetMonitorInfoW(mon, ctypes.byref(info)):
        return 0.0, 0.0, 1280.0, 720.0
    r = info.rcWork
    return r.left / s, r.top / s, r.right / s, r.bottom / s


def _header_visible(x: int, y: int, w: int) -> bool:
    """Bilah atas sticky (tempat menyeret) masih berada di salah satu monitor?"""
    s = _scale()
    rect = wintypes.RECT(int(x * s), int(y * s), int((x + w) * s), int((y + 36) * s))
    return bool(_user32.MonitorFromRect(ctypes.byref(rect), MONITOR_DEFAULTTONULL))


class DesktopApi:
    """Dipanggil dari JavaScript lewat window.pywebview.api (tiap panggilan di thread baru).

    Status disimpan di atribut berawalan garis bawah agar tidak ikut diekspos pywebview.
    """

    def __init__(self, shell: "Shell") -> None:
        self._shell = shell

    def sticky_open(self, note_id):
        return self._shell.open_sticky(str(note_id))

    def sticky_tear(self, note_id):
        return self._shell.open_sticky(str(note_id), follow=True)

    def sticky_close(self, note_id):
        self._shell.close_sticky(str(note_id))
        return True

    def sticky_set_on_top(self, note_id, on):
        return self._shell.set_on_top(str(note_id), bool(on))

    def sticky_resize(self, note_id, width, height):
        self._shell.resize_sticky(str(note_id), width, height)
        return True

    def open_stickies(self):
        return self._shell.open_ids()

    def show_main(self, path=None):
        self._shell.show_main(path)
        return True


class Shell:
    def __init__(self, base_url: str) -> None:
        self.base = base_url.rstrip("/")
        self.api = DesktopApi(self)
        self.main: Optional[webview.Window] = None
        self._stickies: dict[str, webview.Window] = {}
        self._lock = threading.RLock()
        # Cek-lalu-buat jendela harus atomik: panggilan js_api berjalan di thread masing-masing,
        # jadi klik ganda bisa membuat dua jendela. Tidak pernah diambil di thread GUI.
        self._create_lock = threading.Lock()
        self._timers: dict[str, threading.Timer] = {}
        self._quitting = False
        self._tray = None
        self._tray_hint_done = False

    # ---- jendela utama ----------------------------------------------------------------
    def create_main(self, path: str = "/", hidden: bool = False) -> webview.Window:
        win = webview.create_window(f"Daily App {__version__}", self.base + path, js_api=self.api,
                                    width=1280, height=860, min_size=(900, 600), text_select=True,
                                    hidden=hidden)
        win.events.closing += lambda: self._on_main_closing()
        win.events.closed += lambda: self._on_main_closed(win)
        self.main = win
        return win

    def _on_main_closing(self) -> bool:
        # Berjalan di thread GUI: jangan memanggil evaluate_js/destroy di sini.
        if not self._quitting and self._stickies and not _shutting_down():
            self._tray_hint()
        return True

    def _on_main_closed(self, win) -> None:
        with self._lock:
            if self.main is win:
                self.main = None

    def show_main(self, path: Optional[str] = None) -> None:
        with self._create_lock:
            with self._lock:
                win = self.main
            if win is None:
                self.create_main(path or "/")
                return
        if path and self._safe_to_navigate(win):
            win.load_url(self.base + path)
        win.show()
        self._activate(win)

    def _safe_to_navigate(self, win) -> bool:
        """Pindah halaman hanya dari Beranda atau Catatan: halaman lain (invoice, tool,
        watermark) bisa berisi isian yang belum disimpan."""
        try:
            current = urlsplit(win.get_current_url() or "").path
        except Exception:  # noqa: BLE001
            return False
        return current in ("", "/", "/notes")

    # ---- sticky -----------------------------------------------------------------------
    def open_ids(self) -> list[str]:
        with self._lock:
            return list(self._stickies)

    def open_sticky(self, note_id: str, follow: bool = False, prestart: bool = False):
        if notes_store.get_note(note_id) is None:
            return {"ok": False, "error": "Catatan tidak ditemukan."}
        with self._create_lock:
            return self._open_sticky_locked(note_id, follow, prestart)

    def _open_sticky_locked(self, note_id: str, follow: bool, prestart: bool):
        with self._lock:
            existing = self._stickies.get(note_id)
        if existing is not None:
            existing.show()
            self._activate(existing)
            if follow:
                self._start_follow(existing)
            return {"ok": True, "already": True}

        st = sticky_store.get(note_id)
        width, height = st["w"], st["h"]
        if follow:
            cx, cy = _cursor()
            x, y = cx - 60, cy - 16
        elif st["x"] is not None and st["y"] is not None and _header_visible(st["x"], st["y"], width):
            x, y = st["x"], st["y"]
        else:
            x, y = self._default_pos(width, height)

        win = webview.create_window(
            STICKY_TITLE, f"{self.base}/sticky/{note_id}", js_api=self.api,
            x=int(x), y=int(y), width=width, height=height, min_size=config.STICKY_MIN_SIZE,
            frameless=True, easy_drag=False, on_top=st["on_top"], text_select=True,
            hidden=True, shadow=True, background_color=_COLOR_BG.get(st["color"], "#fbf1cf"),
        )
        with self._lock:
            self._stickies[note_id] = win
        win.events.moved += lambda *a: self._persist_later(note_id)
        win.events.resized += lambda *a: self._persist_later(note_id)
        win.events.closed += lambda: self._on_sticky_closed(note_id, win)
        try:
            sticky_store.update(note_id, open=True)
        except OSError:
            log.exception("Gagal menyimpan status sticky %s", note_id)
        if not prestart:
            self.finish_sticky(note_id, win, width, height)
            if follow:
                self._start_follow(win)
        return {"ok": True}

    def finish_sticky(self, note_id: str, win, width: int, height: int) -> None:
        """Setelah jendela dibuat (masih tersembunyi): tanpa tombol taskbar, ukuran tepat,
        pantau alasan penutupan, lalu tampilkan."""
        try:
            from System import Func, Type  # pythonnet, sudah dimuat oleh pywebview

            def prepare():
                hwnd = win.native.Handle.ToInt64()
                # Gaya tool window harus dipasang selagi jendela tersembunyi agar tombol
                # taskbar benar-benar hilang (pywebview resize() ikut menampilkan jendela).
                style = _user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                _user32.SetWindowLongW(hwnd, GWL_EXSTYLE, (style | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW)
                # Jendela tanpa bingkai dibuat sedikit lebih kecil dari permintaan: set ulang
                # ukuran fisiknya tanpa memindah, mengaktifkan, atau menampilkan.
                s = (_user32.GetDpiForWindow(hwnd) or 96) / 96.0
                _user32.SetWindowPos(hwnd, None, 0, 0, int(width * s), int(height * s),
                                     SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE)

            win.native.Invoke(Func[Type](prepare))
            win.native.FormClosing += lambda sender, args: self._on_sticky_form_closing(note_id, args)
        except Exception:  # noqa: BLE001 - kosmetik saja; sticky tetap jalan
            log.exception("Gagal menyiapkan jendela sticky")
        win.show()

    def _default_pos(self, width: int, height: int) -> tuple[float, float]:
        ref = self.main
        try:
            left, top, right, _bottom = _work_area(ref.x, ref.y) if ref else _work_area()
        except Exception:  # noqa: BLE001
            left, top, right, _bottom = _work_area()
        k = len(self._stickies) % 6
        return right - width - 32 - 30 * k, top + 32 + 30 * k

    def _start_follow(self, win) -> None:
        """Sticky mengikuti kursor sampai tombol mouse dilepas (seret keluar dari aplikasi)."""
        def follow():
            off_x, off_y = 60, 16
            deadline = time.time() + 30
            while _mouse_down() and time.time() < deadline:
                cx, cy = _cursor()
                try:
                    win.move(int(cx - off_x), int(cy - off_y))
                except Exception:  # noqa: BLE001 - jendela ditutup saat diseret
                    return
                time.sleep(1 / 60)
            self._activate(win)
        threading.Thread(target=follow, name="sticky-follow", daemon=True).start()

    def close_sticky(self, note_id: str) -> None:
        sticky_store.update(note_id, open=False)
        with self._lock:
            win = self._stickies.get(note_id)
        if win is not None:
            win.destroy()

    def _on_sticky_form_closing(self, note_id: str, args) -> None:
        """FormClosing WinForms (thread GUI). Ditutup pengguna (Alt+F4) = sticky dilepas.
        Ditutup karena Windows mati, logoff, Task Manager, atau installer (Restart Manager),
        atau lewat 'Keluar' di tray: status dibiarkan terbuka agar sticky muncul lagi."""
        try:
            from System.Windows.Forms import CloseReason
            if args.Cancel or self._quitting or args.CloseReason != CloseReason.UserClosing:
                return
            sticky_store.update(note_id, open=False)
        except Exception:  # noqa: BLE001
            log.exception("Gagal mencatat penutupan sticky %s", note_id)

    def _on_sticky_closed(self, note_id: str, win) -> None:
        with self._lock:
            if self._stickies.get(note_id) is win:
                del self._stickies[note_id]
            timer = self._timers.pop(note_id, None)
        if timer:
            timer.cancel()

    def set_on_top(self, note_id: str, on: bool) -> bool:
        with self._lock:
            win = self._stickies.get(note_id)
        if win is not None:
            win.on_top = on
        sticky_store.update(note_id, on_top=on)
        return on

    def resize_sticky(self, note_id: str, width, height) -> None:
        with self._lock:
            win = self._stickies.get(note_id)
        if win is None:
            return
        min_w, min_h = config.STICKY_MIN_SIZE
        win.resize(max(min_w, int(float(width))), max(min_h, int(float(height))))

    def _persist_later(self, note_id: str) -> None:
        """Simpan posisi/ukuran 0,5 detik setelah gerakan terakhir (event moved sangat sering)."""
        def save():
            with self._lock:
                win = self._stickies.get(note_id)
                self._timers.pop(note_id, None)
            if win is None:
                return
            try:
                sticky_store.update(note_id, x=win.x, y=win.y, w=win.width, h=win.height)
            except Exception:  # noqa: BLE001
                log.exception("Gagal menyimpan posisi sticky %s", note_id)

        with self._lock:
            old = self._timers.get(note_id)
            if old:
                old.cancel()
            timer = threading.Timer(0.5, save)
            timer.daemon = True
            self._timers[note_id] = timer
        timer.start()

    def show_all_stickies(self) -> None:
        with self._lock:
            wins = list(self._stickies.values())
        for win in wins:
            win.show()
            self._activate(win)

    # ---- tray, single-instance, keluar -------------------------------------------------
    def _activate(self, win) -> None:
        try:
            from System import Func, Type
            from System.Windows.Forms import FormWindowState

            def act():
                if win.native.WindowState == FormWindowState.Minimized:
                    win.native.WindowState = FormWindowState.Normal
                win.native.Activate()

            win.native.Invoke(Func[Type](act))
        except Exception:  # noqa: BLE001
            log.debug("Gagal mengaktifkan jendela", exc_info=True)

    def _in_thread(self, fn, *args):
        # Aksi dari tray berjalan di thread GUI; membuat jendela harus dari thread lain.
        return lambda *_: threading.Thread(target=fn, args=args, daemon=True).start()

    def create_tray(self, host) -> None:
        from System import Func, Type
        import System.Windows.Forms as WinForms
        from System.Drawing import Icon

        def build():
            tray = WinForms.NotifyIcon()
            try:
                tray.Icon = Icon(str(config.STATIC_DIR / "favicon.ico"))
            except Exception:  # noqa: BLE001
                from System.Drawing import SystemIcons
                tray.Icon = SystemIcons.Application
            tray.Text = "Daily App"
            menu = WinForms.ContextMenuStrip()
            menu.Items.Add("Buka Daily App").Click += self._in_thread(self.show_main)
            menu.Items.Add("Tampilkan semua sticky").Click += self._in_thread(self.show_all_stickies)
            menu.Items.Add(WinForms.ToolStripSeparator())
            menu.Items.Add("Keluar").Click += self._in_thread(self.quit)
            tray.ContextMenuStrip = menu
            tray.DoubleClick += self._in_thread(self.show_main)
            tray.Visible = True
            self._tray = tray

            def dispose(*_):
                tray.Visible = False
                tray.Dispose()

            WinForms.Application.ApplicationExit += dispose

        host.native.Invoke(Func[Type](build))

    def _tray_hint(self) -> None:
        if self._tray is None or self._tray_hint_done:
            return
        self._tray_hint_done = True
        try:
            from System.Windows.Forms import ToolTipIcon
            self._tray.ShowBalloonTip(5000, "Daily App tetap berjalan",
                                      "Sticky note masih ada di desktop. Buka atau keluar lewat ikon ini.",
                                      ToolTipIcon.Info)
        except Exception:  # noqa: BLE001
            log.debug("Balon tray gagal", exc_info=True)

    def listen_for_second_launch(self) -> None:
        handle = _kernel32.CreateEventW(None, False, False, SHOW_EVENT_NAME)
        if not handle:
            return

        def wait():
            while True:  # thread daemon: selesai bersama proses
                _kernel32.WaitForSingleObject(handle, INFINITE)
                if not self._quitting:
                    self.show_main()

        threading.Thread(target=wait, name="show-main-listener", daemon=True).start()

    def quit(self) -> None:
        self._quitting = True
        with self._lock:
            stickies = list(self._stickies.values())
            wins = stickies + ([self.main] if self.main else [])
        for win in stickies:
            # Simpan ketikan yang masih menunggu jeda simpan otomatis sebelum jendela ditutup.
            try:
                win.evaluate_js("window.stickyFlushSync && window.stickyFlushSync()")
            except Exception:  # noqa: BLE001
                log.debug("Flush sticky gagal", exc_info=True)
        for win in wins:
            try:
                win.destroy()
            except Exception:  # noqa: BLE001
                log.debug("Gagal menutup jendela", exc_info=True)


def run(base_url: str, startup: bool = False) -> bool:
    """Jalankan loop jendela. False bila WebView2 tidak bisa dipakai."""
    shell = Shell(base_url)
    pending = sticky_store.restorable_ids()
    first_sticky = None
    if startup:
        if not pending:
            return True  # tidak ada sticky untuk dipulihkan: tidak perlu tampil apa pun
        first_sticky = pending.pop(0)
        shell.open_sticky(first_sticky, prestart=True)
        host = shell._stickies[first_sticky]
    else:
        host = shell.create_main("/")

    def after_start():
        host.events.shown.wait(20)
        try:
            shell.create_tray(host)
        except Exception:  # noqa: BLE001
            log.exception("Ikon tray gagal dibuat")
        shell.listen_for_second_launch()
        if first_sticky:
            st = sticky_store.get(first_sticky)
            shell.finish_sticky(first_sticky, host, st["w"], st["h"])
        for note_id in pending:
            try:
                shell.open_sticky(note_id)
            except Exception:  # noqa: BLE001 - satu sticky gagal tidak menghentikan yang lain
                log.exception("Gagal memulihkan sticky %s", note_id)

    webview.settings["ALLOW_DOWNLOADS"] = True  # unduhan hasil tool memunculkan "Simpan sebagai"
    webview.start(after_start, gui="edgechromium", private_mode=False,
                  storage_path=str(config.USER_DIR / "webview"),
                  localization={"windows.fileFilter.allFiles": "Semua file"})
    return True
