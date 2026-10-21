"""Desain 8 — Kreatif: aksen segitiga diagonal di sudut, nuansa playful."""
from app.invoice_designs._base import (
    WHITE, Doc, InvoiceDesign, footer_section, items_table, meta, party, register_design,
    shade, tint,
)


@register_design
class Kreatif(InvoiceDesign):
    id = "kreatif"
    name = "Kreatif"
    description = "Aksen segitiga diagonal di sudut, cocok untuk bisnis kreatif."
    order = 8
    default_color = "#D85A30"
    uses_accent = True

    def setup(self, d: Doc) -> None:
        d.set_auto_page_break(True, margin=30)

        def corners(doc: Doc) -> None:
            a, W, H = doc.ctx.accent, doc.w, doc.h
            doc.fill(tint(a, 0.55))
            doc.polygon([(W - 95, 0), (W, 0), (W, 55)], style="F")
            doc.fill(a)
            doc.polygon([(W - 60, 0), (W, 0), (W, 34)], style="F")
            doc.fill(tint(a, 0.55))
            doc.polygon([(0, H), (0, H - 38), (60, H)], style="F")
            doc.fill(a)
            doc.polygon([(0, H), (0, H - 22), (34, H)], style="F")

        d.decor = corners

    def render(self, d: Doc) -> None:
        c, a = d.ctx, d.ctx.accent
        y = 15
        if d.logo(d.l_margin, y, 42, 20):
            y += 24
        d.font(28, "B", color=a)
        d.set_xy(d.l_margin, y)
        d.cell(100, 12, "INVOICE")
        y = meta(d, d.l_margin, y + 14, 85, c.meta_rows(), label_color=shade(a, 0.2),
                 align_value="L", label_w=26)
        y2 = party(d, d.right - 80, 62, 80, "DARI", c.profile.get("name", ""),
                   c.company_lines(sep="\n"), title_color=a, align="R")
        y += 6
        y1 = party(d, d.l_margin, y, 95, "DITAGIHKAN KEPADA", c.client.get("name", ""),
                   c.client_lines(), title_color=a)
        d.set_y(max(y1, y2) + 8)

        items_table(d, head_fill=tint(a, 0.82), head_color=shade(a, 0.35), borders="NONE",
                    zebra=tint(a, 0.95), padding=2.2)
        footer_section(d, totals_kw={"total_fill": a, "total_color": WHITE, "radius": 2.5},
                       terbilang_kw={"label_color": a}, info_kw={"title_color": a})
