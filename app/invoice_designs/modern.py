"""Desain 2 — Modern: header blok warna penuh, tabel zebra berwarna."""
from app.invoice_designs._base import (
    WHITE, Doc, InvoiceDesign, footer_section, items_table, meta, party, register_design, tint,
)


@register_design
class Modern(InvoiceDesign):
    id = "modern"
    name = "Modern"
    description = "Header blok warna penuh, tabel zebra, total disorot warna."
    order = 2
    default_color = "#185FA5"
    uses_accent = True

    def render(self, d: Doc) -> None:
        c, a = d.ctx, d.ctx.accent
        d.fill(a)
        d.rect(0, 0, d.w, 44, style="F")
        d.logo(d.l_margin, 11, 45, 22)
        d.font(28, "B", color=WHITE)
        d.set_xy(d.l_margin, 12)
        d.cell(d.content_w, 12, "INVOICE", align="R")
        d.text_at(d.l_margin, 26, d.content_w, c.inv.get("number", ""), size=10,
                  color=tint(a, 0.75), align="R")

        y, col = 54, (d.content_w - 12) / 3
        y1 = party(d, d.l_margin, y, col, "DARI", c.profile.get("name", ""),
                   c.company_lines(sep="\n"), title_color=a)
        y2 = party(d, d.l_margin + col + 6, y, col, "DITAGIHKAN KEPADA",
                   c.client.get("name", ""), c.client_lines(sep="\n"), title_color=a)
        y3 = meta(d, d.right - col, y + 4, col, c.meta_rows(), label_w=22, size=8.5)
        d.set_y(max(y1, y2, y3) + 8)

        items_table(d, head_fill=a, head_color=WHITE, borders="NONE", zebra=tint(a, 0.92),
                    padding=2.2)
        footer_section(d, totals_kw={"total_fill": a, "total_color": WHITE},
                       terbilang_kw={"label_color": a}, info_kw={"title_color": a})
