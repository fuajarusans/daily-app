"""Desain 5 — Elegan: huruf serif, aksen emas, garis ganda."""
from app.invoice_designs._base import (
    BLACK, MUTED, Doc, InvoiceDesign, footer_section, items_table, meta, party,
    register_design, tint,
)


@register_design
class Elegan(InvoiceDesign):
    id = "elegan"
    name = "Elegan"
    description = "Huruf serif, aksen emas, garis ganda yang anggun."
    order = 5
    default_color = "#9A7B4F"
    uses_accent = True

    def setup(self, d: Doc) -> None:
        d.set_margins(20, 18, 20)

    def render(self, d: Doc) -> None:
        c, a = d.ctx, d.ctx.accent
        d.hline(12, a, 0.8, 20, d.w - 20)
        d.hline(13.6, a, 0.25, 20, d.w - 20)
        y = 18
        if d.logo(d.l_margin, y, d.content_w, 16, align="C"):
            y += 19
        y = d.text_at(d.l_margin, y, d.content_w, c.profile.get("name", ""), size=14,
                      style="B", kind="serif", color=BLACK, align="C") + 0.5
        y = d.lines_at(d.l_margin, y, d.content_w, c.company_lines(), size=8,
                       kind="serif", align="C") + 5
        d.font(26, "I", "serif", a)
        d.set_xy(d.l_margin, y)
        d.cell(d.content_w, 11, "Invoice", align="C")
        mid = d.w / 2
        d.hline(y + 13, a, 0.4, mid - 15, mid + 15)

        y += 20
        y1 = party(d, d.l_margin, y, 90, "Ditagihkan kepada", c.client.get("name", ""),
                   c.client_lines(), kind="serif", title_color=a, title_size=8.5, name_size=11)
        y2 = meta(d, d.right - 72, y, 72, c.meta_rows(), kind="serif", label_color=a)
        d.set_y(max(y1, y2) + 8)

        items_table(d, kind="serif", head_color=a, borders="HORIZONTAL_LINES",
                    line_color=tint(a, 0.55), padding=2.4)
        kw = {"kind": "serif", "title_color": a, "color": MUTED}
        footer_section(d, totals_kw={"kind": "serif", "rule": a, "double_rule": True,
                                     "total_color": a, "total_size": 12},
                       terbilang_kw={"kind": "serif", "label_color": a}, info_kw=kw)
