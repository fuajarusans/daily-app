"""Desain 6 — Korporat: sidebar warna di kiri berisi identitas & pembayaran."""
from app.invoice_designs._base import (
    WHITE, Doc, InvoiceDesign, footer_section, items_table, meta, party, payment,
    register_design, tint,
)

SIDEBAR_W = 62


@register_design
class Korporat(InvoiceDesign):
    id = "korporat"
    name = "Korporat"
    description = "Sidebar warna di kiri berisi identitas perusahaan & pembayaran."
    order = 6
    default_color = "#0F6E56"
    uses_accent = True

    def setup(self, d: Doc) -> None:
        d.set_margins(SIDEBAR_W + 10, 18, 15)

        def sidebar(doc: Doc) -> None:
            doc.fill(doc.ctx.accent)
            doc.rect(0, 0, SIDEBAR_W, doc.h, style="F")

        d.decor = sidebar

    def render(self, d: Doc) -> None:
        c, a = d.ctx, d.ctx.accent
        soft = tint(a, 0.7)
        x, w = 10, SIDEBAR_W - 20
        y = 18
        if d.logo(x, y, w, 24, align="L"):
            y += 28
        y = party(d, x, y, w, "", c.profile.get("name", ""), c.company_lines(sep="\n"),
                  name_color=WHITE, line_color=soft, name_size=11, line_size=8) + 10
        y = party(d, x, y, w, "DITAGIHKAN KEPADA", c.client.get("name", ""),
                  c.client_lines(sep="\n"), title_color=soft, name_color=WHITE,
                  line_color=soft, name_size=10, line_size=8) + 10
        payment(d, x, y, w, title="PEMBAYARAN", title_color=soft, color=WHITE, size=8)

        d.font(30, "B", color=a)
        d.set_xy(d.l_margin, 16)
        d.cell(d.content_w, 14, "INVOICE")
        y = meta(d, d.l_margin, 36, 90, c.meta_rows(), align_value="L")
        d.set_y(y + 10)
        items_table(d, head_fill=a, head_color=WHITE, borders="NONE", zebra=tint(a, 0.9),
                    padding=2, size=8.5)
        footer_section(d, totals_w=72, show_payment=False, terbilang_full=True,
                       totals_kw={"total_fill": a, "total_color": WHITE},
                       terbilang_kw={"label_color": a}, info_kw={"title_color": a})
