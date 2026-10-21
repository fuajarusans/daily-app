"""Desain 7 — Bold: judul sangat besar, kontras tinggi, bar total gelap."""
from app import invoice_format as fmt
from app.invoice_designs._base import (
    BLACK, MUTED, WHITE, Doc, InvoiceDesign, items_table, meta, notes, paid_stamp, party,
    payment, register_design, terbilang,
)


@register_design
class Bold(InvoiceDesign):
    id = "bold"
    name = "Bold"
    description = "Judul sangat besar, kontras tinggi, bar total gelap."
    order = 7
    default_color = "#1F1F1F"
    uses_accent = True

    def render(self, d: Doc) -> None:
        c, a = d.ctx, d.ctx.accent
        d.font(44, "B", color=BLACK)
        d.set_xy(d.l_margin - 1, 14)
        d.cell(110, 18, "INVOICE")
        y = 14
        if d.logo(d.right - 50, y, 50, 14, align="R"):
            y += 16
        y = d.text_at(d.right - 80, y, 80, c.profile.get("name", ""), size=10.5, style="B",
                      color=BLACK, align="R")
        y = d.lines_at(d.right - 80, y + 0.5, 80, c.company_lines(sep="\n"), size=8, align="R")
        y = max(y, 36) + 3
        d.fill(a)
        d.rect(d.l_margin, y, d.content_w, 2.2, style="F")

        y += 8
        y1 = party(d, d.l_margin, y, 95, "DITAGIHKAN KEPADA", c.client.get("name", ""),
                   c.client_lines(), name_size=13)
        y2 = meta(d, d.right - 75, y, 75, c.meta_rows(), size=9.5, row_h=5.5)
        d.set_y(max(y1, y2) + 8)

        items_table(d, head_fill=a, head_color=WHITE, borders="HORIZONTAL_LINES", padding=2.4)

        # Rincian (subtotal/diskon/PPN) di kanan, lalu bar TOTAL selebar halaman.
        d.ensure_space(75)
        y = d.get_y() + 5
        paid_stamp(d, d.l_margin + 50, y)
        x_tot, w_tot = d.right - 80, 80
        for label, value in c.total_rows():
            d.font(9, color=MUTED)
            d.set_xy(x_tot, y)
            d.cell(40, 6, d.t(label))
            d.font(9, color=BLACK)
            d.cell(w_tot - 42, 6, d.t(value), align="R")
            y += 6
        y += 3
        d.fill(a)
        d.rect(d.l_margin, y, d.content_w, 14, style="F")
        d.font(10, "B", color=WHITE)
        d.set_xy(d.l_margin + 4, y)
        d.cell(80, 14, "TOTAL TAGIHAN")
        d.font(17, "B", color=WHITE)
        d.set_xy(d.l_margin, y)
        d.cell(d.content_w - 4, 14, fmt.rupiah(c.totals["total"]), align="R")
        y = terbilang(d, d.l_margin, y + 19, d.content_w, color=BLACK) + 7
        d.set_y(y)
        d.ensure_space(25)
        y = d.get_y()
        half = (d.content_w - 10) / 2
        payment(d, d.l_margin, y, half)
        notes(d, d.l_margin + half + 10, y, half, color=MUTED)
