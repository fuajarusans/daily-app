"""Objek template Jinja2 bersama untuk semua route (agar variabel global seragam)."""
from fastapi.templating import Jinja2Templates
from markupsafe import Markup, escape

from app import config
from app.version import __version__

ICON_SPRITE = "/static/vendor/tabler-sprite.svg"


def icon(name: str, cls: str = "") -> Markup:
    """Ikon dari sprite Tabler, mis. {{ icon('eraser') }}. Dekoratif (aria-hidden)."""
    return Markup(
        f'<svg class="ico {escape(cls)}" aria-hidden="true" focusable="false">'
        f'<use href="{ICON_SPRITE}#{escape(name)}"></use></svg>'
    )


templates = Jinja2Templates(directory=str(config.TEMPLATE_DIR))
templates.env.globals["app_version"] = __version__
templates.env.globals["icon"] = icon
templates.env.globals["file_ttl_hours"] = max(1, config.FILE_TTL_SECONDS // 3600)
