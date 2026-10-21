"""Desain 9 — Ringkas: rapat & hemat kertas, semua informasi dalam ruang sempit."""
from app.invoice_designs._base import (
    BLACK, MUTED, Doc, InvoiceDesign, footer_section, items_table, meta, register_design,
)

LIGHT = (205, 205, 205)


@register_design
class Ringkas(InvoiceDesign):
    id = "ringkas"
    name = "Ringkas"
    description = "Rapat & hemat kertas; semua informasi dalam ruang sempit."
    order = 9

    def setup(self, d: Doc) -> None:
        d.set_margins(10, 10, 10)
        d.set_auto_page_break(True, margin=15)

    def render(self, d: Doc) -> None:
        c = d.ctx
        lw = d.logo(d.l_margin, 10, 22, 12)
        x = d.l_margin + (lw + 3 if lw else 0)
        y = d.text_at(x, 10, 105, c.profile.get("name", ""), size=10.5, style="B", color=BLACK)
        y = d.lines_at(x, y, 105, [" · ".join(c.company_lines(sep=" · "))], size=7.5)
        d.font(12, "B", color=BLACK)
        d.set_xy(d.right - 62, 10)
        d.cell(62, 6, "INVOICE", align="R")
        y2 = meta(d, d.right - 62, 16, 62, c.meta_rows(), size=7.5, row_h=3.8, label_w=20)
        y = max(y, y2, 23) + 2
        d.hline(y, BLACK, 0.3)

        y += 2.5
        d.font(7.5, "B", color=MUTED)
        d.set_xy(d.l_margin, y)
        d.cell(16, 4, "Kepada:")
        client = " · ".join([c.client.get("name", "")] + c.client_lines(sep=" · "))
        y = d.text_at(d.l_margin + 16, y, d.content_w - 16, client, size=8, color=BLACK, lh=4)
        d.set_y(y + 3)

        items_table(d, borders="HORIZONTAL_LINES", line_color=LIGHT, size=8, padding=1,
                    head_fill=(240, 240, 240))
        footer_section(d, gap=3, totals_w=70,
                       totals_kw={"size": 8, "row_h": 4.5, "total_size": 9.5},
                       terbilang_kw={"size": 7.5}, info_kw={"size": 7.5})
