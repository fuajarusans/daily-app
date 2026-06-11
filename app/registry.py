"""Tool registry pusat.

Setiap tool adalah subclass dari `Tool` dan didaftarkan dengan decorator
`@register_tool`. Dashboard membaca registry ini untuk menampilkan daftar tool
secara otomatis — tidak perlu mengubah kode dashboard saat menambah tool baru.

Cara menambah tool baru (ringkas):
    1. Buat file baru di folder `tools/`, mis. `tools/contoh.py`
    2. Definisikan subclass `Tool`, isi metadata + method `process()`
    3. Beri decorator `@register_tool`
    4. Selesai — tool langsung muncul di dashboard.

Lihat README.md untuk contoh lengkap.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional


class ToolError(Exception):
    """Error 'ramah' yang pesannya aman ditampilkan ke pengguna di UI."""


class Tool:
    """Kontrak dasar sebuah tool.

    Subclass wajib mengisi metadata di bawah dan meng-override `process()`.
    """

    # --- Metadata (wajib diisi subclass) ---
    id: str = ""                       # ID unik & URL-friendly, mis. "pdf-to-word"
    name: str = ""                     # Nama tampil, mis. "PDF ke Word"
    description: str = ""              # Deskripsi singkat untuk kartu dashboard
    icon: str = "🛠️"                   # Emoji ikon

    # Ekstensi input yang diterima (huruf kecil, dengan titik). [] = bebas/tanpa file.
    accepted_extensions: list[str] = []

    # Apakah tool menerima banyak file sekaligus (batch).
    supports_batch: bool = False

    # Apakah tool butuh input file sama sekali (mis. QR code tidak butuh file).
    requires_file: bool = True

    # Opsi form tambahan (deklaratif). Lihat README untuk skema lengkap.
    # Contoh: {"name": "quality", "label": "Kualitas", "type": "range",
    #          "min": 1, "max": 100, "default": 80}
    options: list[dict[str, Any]] = []

    # --- Logika ---
    def check_dependencies(self) -> Optional[str]:
        """Kembalikan None bila siap dipakai, atau string pesan bila ada
        dependency eksternal yang belum terpasang. Pesan ditampilkan di UI."""
        return None

    def process(
        self,
        input_paths: list[Path],
        options: dict[str, Any],
        output_dir: Path,
    ) -> list[Path]:
        """Proses utama tool.

        Args:
            input_paths: daftar path file upload (kosong bila requires_file=False).
            options: nilai opsi form dari pengguna (sudah dikonversi tipe dasar).
            output_dir: folder tujuan untuk menulis file hasil.

        Returns:
            Daftar path file hasil. Bila >1 file (atau batch), framework akan
            otomatis membungkusnya menjadi satu .zip saat diunduh.

        Raises:
            ToolError: untuk kegagalan yang pesannya aman ditampilkan ke pengguna.
        """
        raise NotImplementedError

    # --- Serialisasi untuk frontend ---
    def to_dict(self) -> dict[str, Any]:
        dep_msg = self.check_dependencies()
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "accepted_extensions": self.accepted_extensions,
            "supports_batch": self.supports_batch,
            "requires_file": self.requires_file,
            "options": self.options,
            "ready": dep_msg is None,
            "dependency_message": dep_msg,
        }


# Registry global: id -> instance Tool
_REGISTRY: dict[str, Tool] = {}


def register_tool(cls: type[Tool]) -> type[Tool]:
    """Decorator untuk mendaftarkan sebuah tool ke registry pusat."""
    instance = cls()
    if not instance.id:
        raise ValueError(f"Tool {cls.__name__} tidak punya 'id'.")
    if instance.id in _REGISTRY:
        raise ValueError(f"Tool dengan id '{instance.id}' sudah terdaftar.")
    _REGISTRY[instance.id] = instance
    return cls


def get_tool(tool_id: str) -> Optional[Tool]:
    return _REGISTRY.get(tool_id)


def all_tools() -> list[Tool]:
    """Semua tool, diurutkan berdasarkan nama untuk tampilan rapi."""
    return sorted(_REGISTRY.values(), key=lambda t: t.name.lower())
