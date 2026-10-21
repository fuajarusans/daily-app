"""Desain 4 — Spreadsheet: grid penuh & padat, cocok untuk invoice dengan banyak item."""
from fpdf import FontFace

from app.invoice_designs._base import (
    BLACK, Doc, InvoiceDesign, footer_section, items_table, register_design,
)

GRID = (150, 150, 150)
HEAD = (225, 225, 225)


@register_design
class Spreadsheet(InvoiceDesign):
    id = "spreadsheet"
    name = "Spreadsheet"
    description = "Grid penuh & padat, hemat ruang untuk banyak item."
    order = 4

    def setup(self, d: Doc) -> None:
        d.set_margins(12, 12, 12)

    def _grid(self, d: Doc, heads: list[str], values: list[str]) -> None:
        d.draw(GRID, 0.2)
        d.font(8.5, color=BLACK)
        with d.table(width=d.content_w, align="LEFT", line_height=4, padding=1.5,
                     headings_style=FontFace(emphasis="BOLD", fill_color=HEAD, size_pt=8)) as t:
            r = t.row()
            for h in heads:
                r.cell(d.t(h))
            r = t.row()
            for v in values:
                r.cell(d.t(v))
        d.set_y(d.get_y() + 3)

    def render(self, d: Doc) -> None:
        c = d.ctx
        lw = d.logo(d.l_margin, 12, 28, 14)
        x = d.l_margin + (lw + 3 if lw else 0)
        d.text_at(x, 13, 110, c.profile.get("name", ""), size=12, style="B", color=BLACK)
        d.font(18, "B", color=BLACK)
        d.set_xy(d.l_margin, 12)
        d.cell(d.content_w, 10, "INVOICE", align="R")
        d.set_y(30)
        number, tgl, due = (v for _, v in c.meta_rows())
        self._grid(d, ["No. Invoice", "Tanggal", "Jatuh tempo", "Mata uang"],
                   [number, tgl, due, "IDR (Rupiah)"])
        company = "\n".join([c.profile.get("name", "")] + c.company_lines(sep=" · "))
        client = "\n".join([c.client.get("name", "")] + c.client_lines(sep=" · "))
        self._grid(d, ["Dari", "Ditagihkan kepada"], [company, client])

        items_table(d, head_fill=HEAD, line_color=GRID, size=8.5, padding=1.2)
        footer_section(d, gap=4, totals_kw={"row_lines": GRID, "rule": GRID, "size": 8.5,
                                            "row_h": 5.5, "total_size": 10})
