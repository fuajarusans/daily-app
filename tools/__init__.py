"""Auto-import semua modul tool di folder ini.

Cukup letakkan file `.py` baru di folder `tools/` dan beri decorator
`@register_tool` pada subclass `Tool` di dalamnya — file akan otomatis dimuat
saat aplikasi start, tanpa perlu menyentuh kode lain.
"""
import importlib
import pkgutil
from pathlib import Path

_package_dir = Path(__file__).resolve().parent

for module_info in pkgutil.iter_modules([str(_package_dir)]):
    name = module_info.name
    if name.startswith("_"):
        continue  # lewati modul privat (mis. _helpers.py)
    importlib.import_module(f"{__name__}.{name}")
