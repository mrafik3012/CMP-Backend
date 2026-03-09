"""PDF generation for logs/reports. FR-LOG-003, Report Templates 8.1.
Uses ReportLab Canvas API; writes to temp file then reads back for reliable output on all platforms.
"""
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Any


def _safe(s: str, max_len: int = 80) -> str:
    """Ensure string is safe for Helvetica (ASCII) and truncate."""
    if s is None:
        return ""
    out = str(s).encode("ascii", "replace").decode("ascii")[:max_len]
    return out or "-"


def _minimal_pdf_bytes_fallback() -> bytes:
    """Fixed fallback when dynamic message would break PDF structure."""
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n"
        b"2 0 obj\n<</Type/Pages/Kids[3 0 R]/Count 1>>\nendobj\n"
        b"3 0 obj\n<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Contents 4 0 R>>\nendobj\n"
        b"4 0 obj\n<</Length 44>>\nstream\nBT /F1 12 Tf 72 720 Td (PDF unavailable.) Tj ET\nendstream\nendobj\n"
        b"5 0 obj\n<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>\nendobj\n"
        b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000052 00000 n \n0000000115 00000 n \n0000000206 00000 n \n0000000290 00000 n \n"
        b"trailer\n<</Size 6/Root 1 0 R>>\nstartxref\n378\n%%EOF\n"
    )


def _canvas_to_bytes(draw_fn) -> bytes:
    """Run draw_fn(canvas), then return PDF bytes from temp file (avoids BytesIO issues on some systems)."""
    fd, path = tempfile.mkstemp(suffix=".pdf")
    try:
        import os
        os.close(fd)
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(path, pagesize=A4)
        draw_fn(c)
        c.save()
        return Path(path).read_bytes()
    finally:
        try:
            Path(path).unlink(missing_ok=True)
        except Exception:
            pass


# App-aligned PDF palette (from frontend index.css)
_PDF = {
    "text_primary": "#0f1419",
    "text_secondary": "#64748b",
    "primary": "#ffb020",       # brand gold
    "secondary": "#5b7cff",     # accent blue
    "surface": "#ffffff",
    "card": "#eef1f6",
    "border": "#e2e8f0",
    "success": "#2fbf71",
    "warning": "#f5a524",
    "muted": "#94a3b8",
    "header_bg": "#0f1419",
    "white": "#ffffff",
}

# Brand (align with frontend src/config/brand.ts)
_BRAND = {
    "name": "BuildDesk",
    "tagline": "Built to Build",
    "initials": "BD",
}


def _draw_data_table(c, mx: float, y_list: list, col_widths: list, headers: list, rows: list, *,
                    row_h: float = 20, card, border, text_primary, text_secondary, page_h: float = 842,
                    min_y: float = 70, alternate_fill=None) -> None:
    """Draw a table: header row + data rows with borders. Updates y_list[0]. Optionally alternate row fill."""
    from reportlab.lib.colors import HexColor
    y = y_list[0]
    total_w = sum(col_widths)
    # Header
    if y < min_y:
        c.showPage()
        y_list[0] = page_h - 40
        y = y_list[0]
    c.setFillColor(card)
    c.setStrokeColor(border)
    c.rect(mx, y - row_h, total_w, row_h, fill=1, stroke=1)
    c.setFillColor(text_primary)
    c.setFont("Helvetica-Bold", 9)
    x = mx
    for i, h in enumerate(headers):
        c.drawString(x + 6, y - row_h + (row_h - 10) / 2 + 2, _safe(h, 30))
        x += col_widths[i]
    y -= row_h
    c.setFont("Helvetica", 9)
    for idx, row_cells in enumerate(rows):
        if y < min_y:
            c.showPage()
            y_list[0] = page_h - 40
            y = y_list[0]
        if alternate_fill and idx % 2 == 1:
            c.setFillColor(alternate_fill)
            c.rect(mx, y - row_h, total_w, row_h, fill=1, stroke=0)
        c.setStrokeColor(border)
        c.rect(mx, y - row_h, total_w, row_h, fill=0, stroke=1)
        c.setFillColor(text_primary)
        x = mx
        for i, cell in enumerate(row_cells):
            if i < len(col_widths):
                c.drawString(x + 6, y - row_h + (row_h - 8) / 2 + 2, _safe(str(cell) if cell is not None else "—", 40))
                x += col_widths[i]
        y -= row_h
    y_list[0] = y


def _draw_brand_block(c, x: float, y: float, primary, white, text_primary, text_secondary, *, small: bool = False, name_color=None) -> None:
    """Draw logo mark (initials in primary box) + brand name; optional tagline. name_color defaults to white (for dark header)."""
    from reportlab.lib.colors import HexColor
    name_fill = name_color if name_color is not None else white
    box = 28 if small else 36
    pad = 4 if small else 6
    c.setFillColor(primary)
    c.rect(x, y - box, box, box, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 10 if small else 12)
    bd_y = y - box + (box - 8) / 2 + 6
    c.drawString(x + 6 if small else x + 8, bd_y, _BRAND["initials"])
    c.setFillColor(name_fill)
    c.setFont("Helvetica-Bold", 10 if small else 12)
    c.drawString(x + box + pad, y - 10 if small else y - 12, _BRAND["name"])
    if not small:
        c.setFillColor(HexColor("#94a3b8"))
        c.setFont("Helvetica", 8)
        c.drawString(x + box + pad, y - 24, _BRAND["tagline"])


def _reportlab_project_summary(project_name: str, content: dict[str, Any]) -> bytes:
    """Generate project summary PDF with app colors, brand, section formatting, and spacing."""
    from reportlab.lib.colors import HexColor

    text_primary = HexColor(_PDF["text_primary"])
    text_secondary = HexColor(_PDF["text_secondary"])
    primary = HexColor(_PDF["primary"])
    white = HexColor(_PDF["white"])
    card = HexColor(_PDF["card"])
    border = HexColor(_PDF["border"])
    header_bg = HexColor(_PDF["header_bg"])
    mx = 56
    page_w, page_h = 595, 842
    bar_h = 60
    section_gap = 24
    row_h = 24

    def draw(c):
        # Header with brand
        c.setFillColor(header_bg)
        c.rect(0, page_h - bar_h, page_w, bar_h, fill=1, stroke=0)
        c.setFillColor(primary)
        c.rect(0, page_h - bar_h, page_w, 3, fill=1, stroke=0)
        _draw_brand_block(c, mx, page_h - 14, primary, white, text_primary, text_secondary, small=False)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 15)
        c.drawString(mx + 200, page_h - 30, "PROJECT SUMMARY")
        c.setFont("Helvetica", 9)
        c.setFillColor(HexColor("#cbd5e1"))
        c.drawString(mx + 200, page_h - 46, _safe(content.get("name") or project_name, 50))
        y = page_h - bar_h - 32

        # Section: Overview (with bar + rule like daily report)
        c.setFillColor(primary)
        c.rect(mx, y - 16, 4, 16, fill=1, stroke=0)
        c.setFillColor(text_primary)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(mx + 10, y - 20, "Overview")
        c.setStrokeColor(border)
        c.setLineWidth(0.25)
        c.line(mx, y - 26, page_w - mx, y - 26)
        y -= 44

        # Overview as a proper table (header + data rows)
        detail_w = page_w - 2 * mx
        c.setFillColor(card)
        c.setStrokeColor(border)
        c.rect(mx, y - row_h, detail_w, row_h, fill=1, stroke=1)
        c.setFillColor(text_primary)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(mx + 10, y - row_h + 6, "Field")
        c.drawString(mx + 160, y - row_h + 6, "Value")
        y -= row_h
        rows = [
            ("Project", _safe(content.get("name") or project_name, 50)),
            ("Client", _safe(content.get("client"), 50)),
            ("Location", _safe(content.get("location"), 50)),
            ("Start date", _safe(str(content.get("start_date", "-")), 20)),
            ("End date", _safe(str(content.get("end_date", "-")), 20)),
            ("Estimated budget", _safe(str(content.get("estimated_budget", "-")), 24)),
            ("Status", _safe(str(content.get("status", "-")), 20)),
        ]
        c.setFont("Helvetica", 10)
        for idx, (label, value) in enumerate(rows):
            if idx % 2 == 1:
                c.setFillColor(HexColor("#f8fafc"))
                c.rect(mx, y - row_h, detail_w, row_h, fill=1, stroke=0)
            c.setFillColor(border)
            c.rect(mx, y - row_h, detail_w, row_h, fill=0, stroke=1)
            c.setFillColor(text_secondary)
            c.drawString(mx + 10, y - row_h + 7, label)
            c.setFillColor(text_primary)
            c.drawString(mx + 160, y - row_h + 7, value)
            y -= row_h
        y -= section_gap

        # Footer with brand
        c.setStrokeColor(primary)
        c.setLineWidth(1)
        c.line(mx, 56, page_w - mx, 56)
        _draw_brand_block(c, mx, 42, primary, white, text_primary, text_secondary, small=True, name_color=text_primary)
        c.setFillColor(text_secondary)
        c.setFont("Helvetica", 8)
        c.drawString(mx + 118, 36, f"{_BRAND['name']} — Project Summary")
        c.showPage()

    return _canvas_to_bytes(draw)


def _format_report_date(date_str: str) -> str:
    """Format YYYY-MM-DD as '07 Mar, 2026'."""
    try:
        from datetime import datetime
        d = datetime.strptime(str(date_str).strip()[:10], "%Y-%m-%d")
        return d.strftime("%d %b, %Y")
    except Exception:
        return str(date_str)[:10]


def _reportlab_daily_report(
    project_name: str,
    payload: dict[str, Any],
    *,
    report_title: str = "DAILY SITE REPORT",
    report_subtitle: str | None = None,
    footer_label: str = "Daily Site Report",
) -> bytes:
    """Generate daily (or weekly/monthly) report PDF with app colors and authority-style layout."""
    from reportlab.lib.colors import HexColor

    date_fmt_for_sub = _format_report_date(payload.get("report_date", "") or "") if report_subtitle is None else report_subtitle
    p = _PDF
    text_primary = HexColor(p["text_primary"])
    text_secondary = HexColor(p["text_secondary"])
    primary = HexColor(p["primary"])
    white = HexColor(p["white"])
    card = HexColor(p["card"])
    border = HexColor(p["border"])
    success = HexColor(p["success"])
    warning = HexColor(p["warning"])
    muted = HexColor(p["muted"])
    header_bg = HexColor(p["header_bg"])

    # Spacing constants
    section_gap = 28
    line_height = 16
    after_title = 8

    def draw(c):
        page_w, page_h = 595, 842  # A4
        margin = 56
        y = [page_h - 40]
        mx = margin

        def _y(step: float = line_height) -> float:
            y[0] -= step
            return y[0]

        def _section_title(title: str) -> None:
            if y[0] < 140:
                c.showPage()
                y[0] = page_h - 40
            _y(section_gap * 0.4)
            c.setFillColor(primary)
            c.rect(mx, y[0] - 16, 4, 16, fill=1, stroke=0)
            c.setFillColor(text_primary)
            c.setFont("Helvetica-Bold", 12)
            c.drawString(mx + 10, _y(20), _safe(title, 60))
            c.setStrokeColor(border)
            c.setLineWidth(0.25)
            c.line(mx, y[0] - 2, page_w - margin, y[0] - 2)
            _y(after_title)
            c.setFillColor(text_primary)

        def _line(text: str, max_len: int = 95) -> None:
            if y[0] < 70:
                c.showPage()
                y[0] = page_h - 40
            c.setFont("Helvetica", 9)
            c.setFillColor(text_primary)
            c.drawString(mx, _y(), _safe(text, max_len))

        # ---- Header: brand + report title + prepared by ----
        bar_h = 60
        c.setFillColor(header_bg)
        c.rect(0, page_h - bar_h, page_w, bar_h, fill=1, stroke=0)
        c.setFillColor(primary)
        c.rect(0, page_h - bar_h, page_w, 3, fill=1, stroke=0)
        _draw_brand_block(c, mx, page_h - 18, primary, white, text_primary, text_secondary, small=False)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 15)
        c.drawString(mx + 200, page_h - 30, report_title)
        c.setFont("Helvetica", 9)
        c.setFillColor(HexColor("#cbd5e1"))
        c.drawString(mx + 200, page_h - 46, f"{date_fmt_for_sub}  •  {_safe(project_name, 40)}")
        created = _safe(payload.get("created_by_name") or "—", 28)
        c.setFont("Helvetica", 9)
        c.drawString(page_w - margin - 130, page_h - 36, f"Prepared by {created}")
        _y(bar_h + 12)
        c.setFillColor(text_primary)

        # ---- Project context card ----
        box_h = 44
        c.setFillColor(card)
        c.setStrokeColor(border)
        c.setLineWidth(0.5)
        c.rect(mx, y[0] - box_h, page_w - 2 * margin, box_h, fill=1, stroke=1)
        c.setFillColor(text_primary)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(mx + 14, y[0] - 18, _safe(project_name, 55))
        c.setFont("Helvetica", 9)
        c.setFillColor(text_secondary)
        weather = payload.get("weather") or "-"
        temp = payload.get("temperature")
        temp_str = f" {temp}°C" if temp is not None and str(temp).strip() else ""
        shift_s = payload.get("shift_start") or "-"
        shift_e = payload.get("shift_end") or "-"
        c.drawString(mx + 14, y[0] - 36, f"Period: {date_fmt_for_sub}  •  Weather: {weather}{temp_str}  •  Shift: {shift_s} – {shift_e}")
        _y(box_h + section_gap)
        c.setFillColor(text_primary)

        wi = payload.get("work_items") or []
        iss = payload.get("issues") or []
        wf = payload.get("workforce") or []
        wi_with_data = [w for w in wi if (w.get("task_name") or "").strip()]
        wf_with_data = [w for w in wf if (w.get("trade") or "").strip() or int(w.get("present") or 0) != 0 or int(w.get("absent") or 0) != 0 or int(w.get("total") or 0) != 0]
        total_present = sum(int(w.get("present") or 0) for w in wf)

        # ---- Tasks summary cards – only show when there are work items ----
        if wi_with_data:
            completed = sum(1 for w in wi_with_data if (float(w.get("progress_cumulative") or 0)) >= 100)
            in_progress = sum(1 for w in wi_with_data if 0 < (float(w.get("progress_cumulative") or 0)) < 100)
            not_started = sum(1 for w in wi_with_data if (float(w.get("progress_cumulative") or 0)) == 0)
            _section_title("Tasks Summary")
            card_w = (page_w - 2 * margin - 16) / 3
            card_h = 50
            for i, (label, count, fill_col, bar_col) in enumerate([
                ("COMPLETED", completed, success, success),
                ("IN PROGRESS", in_progress, warning, warning),
                ("NOT STARTED", not_started, muted, muted),
            ]):
                cx = mx + i * (card_w + 8)
                c.setFillColor(fill_col)
                c.setStrokeColor(border)
                c.rect(cx, y[0] - card_h, card_w, card_h, fill=1, stroke=1)
                c.setFillColor(bar_col)
                c.rect(cx, y[0] - card_h, 4, card_h, fill=1, stroke=0)
                c.setFillColor(text_primary)
                c.setFont("Helvetica-Bold", 9)
                c.drawString(cx + 12, y[0] - 22, label)
                c.setFont("Helvetica", 12)
                c.drawString(cx + 12, y[0] - 42, str(count))
            _y(card_h + section_gap)
        c.setFillColor(text_primary)

        # ---- Activity – only show when there is something to summarize ----
        if wi_with_data or iss or wf_with_data:
            _section_title("Activity")
            c.setFont("Helvetica", 9)
            c.setFillColor(text_secondary)
            c.drawString(mx, _y(), f"Task updates: {len(wi_with_data)}  •  Issues: {len(iss)}  •  On-site: {total_present}")
            _y(section_gap * 0.5)
        c.setFillColor(text_primary)

        # ---- Attendance table – only show when there are entries ----
        if wf_with_data:
            _section_title("Attendance")
            col_w = [140, 70, 70, 70]
            row_h = 20
            c.setFillColor(card)
            c.setStrokeColor(border)
            c.rect(mx, y[0] - row_h, sum(col_w), row_h, fill=1, stroke=1)
            c.setFillColor(text_primary)
            c.setFont("Helvetica-Bold", 9)
            c.drawString(mx + 8, y[0] - 14, "Labour / Vendor")
            c.drawString(mx + col_w[0] + 8, y[0] - 14, "Present")
            c.drawString(mx + col_w[0] + col_w[1] + 8, y[0] - 14, "Absent")
            c.drawString(mx + col_w[0] + col_w[1] + col_w[2] + 8, y[0] - 14, "Total")
            _y(row_h)
            c.setFont("Helvetica", 9)
            for idx, w in enumerate(wf_with_data):
                if y[0] < 90:
                    c.showPage()
                    y[0] = page_h - 40
                if idx % 2 == 1:
                    c.setFillColor(HexColor("#f8fafc"))
                    c.rect(mx, y[0] - row_h, sum(col_w), row_h, fill=1, stroke=0)
                c.setFillColor(border)
                c.rect(mx, y[0] - row_h, sum(col_w), row_h, fill=0, stroke=1)
                c.setFillColor(text_primary)
                trade = _safe(w.get("trade") or "—", 22)
                p, a, t = int(w.get("present") or 0), int(w.get("absent") or 0), int(w.get("total") or 0)
                c.drawString(mx + 8, y[0] - 14, trade)
                c.drawString(mx + col_w[0] + 8, y[0] - 14, str(p))
                c.drawString(mx + col_w[0] + col_w[1] + 8, y[0] - 14, str(a))
                c.drawString(mx + col_w[0] + col_w[1] + col_w[2] + 8, y[0] - 14, str(t))
                _y(row_h)
            _y(section_gap)
        c.setFillColor(text_primary)

        # ---- Work done today (table) – only show when there are entries ----
        if wi_with_data:
            _section_title("Work Done Today")
            work_cols = [180, 75, 55, 52, 52]
            work_headers = ["Task", "Location", "BOQ", "Today %", "Cum. %"]
            work_rows = [
                [w.get("task_name") or "—", w.get("location") or "—", w.get("boq_item") or "—", f"{w.get('progress_today', '')}%", f"{w.get('progress_cumulative', '')}%"]
                for w in wi_with_data
            ]
            _draw_data_table(c, mx, y, work_cols, work_headers, work_rows, row_h=20, card=card, border=border,
                            text_primary=text_primary, text_secondary=text_secondary, page_h=page_h, min_y=70,
                            alternate_fill=HexColor("#f8fafc"))
            _y(section_gap)
        c.setFillColor(text_primary)

        # ---- Materials (table) – only show when there are entries ----
        mat = payload.get("materials") or []
        mat_with_data = [m for m in mat if (m.get("item_name") or "").strip()]
        if mat_with_data:
            _section_title("Materials Delivered")
            mat_cols = [140, 70, 120, 80]
            mat_headers = ["Item", "Quantity", "Supplier", "Status"]
            mat_rows = [[m.get("item_name") or "—", m.get("quantity") or "—", m.get("supplier") or "—", m.get("status") or "—"] for m in mat_with_data]
            _draw_data_table(c, mx, y, mat_cols, mat_headers, mat_rows, row_h=20, card=card, border=border,
                            text_primary=text_primary, text_secondary=text_secondary, page_h=page_h, min_y=70,
                            alternate_fill=HexColor("#f8fafc"))
            _y(section_gap)
        c.setFillColor(text_primary)

        # ---- Issues / Delays (table) – only show when there are entries ----
        iss_with_data = [i for i in iss if (i.get("description") or "").strip()]
        if iss_with_data:
            _section_title("Issues / Delays")
            iss_cols = [72, 260, 60, 85]
            iss_headers = ["Type", "Description", "Impact", "Responsible"]
            iss_rows = [
                [i.get("issue_type") or "—", (i.get("description") or "—")[:60], i.get("impact") or "—", i.get("responsible_party") or "—"]
                for i in iss_with_data
            ]
            _draw_data_table(c, mx, y, iss_cols, iss_headers, iss_rows, row_h=20, card=card, border=border,
                            text_primary=text_primary, text_secondary=text_secondary, page_h=page_h, min_y=70,
                            alternate_fill=HexColor("#f8fafc"))
            _y(section_gap)
        c.setFillColor(text_primary)

        # ---- Payables – only show when there are entries ----
        payables = payload.get("payables") or []
        payables_with_data = [p for p in payables if p and (str(p).strip() if isinstance(p, str) else True)]
        if payables_with_data:
            _section_title("Payables")
            for p in payables_with_data:
                if isinstance(p, dict):
                    _line(str(p.get("description") or p.get("amount") or p))
                else:
                    _line(str(p))
            _y(section_gap)

        # ---- Footer: brand + confidential ----
        c.setStrokeColor(primary)
        c.setLineWidth(1)
        c.line(mx, 56, page_w - mx, 56)
        _draw_brand_block(c, mx, 42, primary, white, text_primary, text_secondary, small=True, name_color=text_primary)
        c.setFillColor(text_secondary)
        c.setFont("Helvetica", 8)
        c.drawString(mx + 118, 36, f"{_BRAND['name']} — {footer_label}")
        c.setFillColor(primary)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(mx + 118, 26, "Confidential")
        c.setFillColor(text_secondary)
        c.drawString(page_w - mx - 24, 34, "1")
        c.showPage()

    return _canvas_to_bytes(draw)


def render_log_pdf(project_name: str, log_date: str, content: dict) -> bytes:
    """Generate PDF for daily log. Prefers ReportLab (reliable on Windows)."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        work = (content.get("work_completed") or "").replace("<", "").replace(">", "")[:2000]
        issues = (content.get("issues") or "").replace("<", "").replace(">", "")[:1000]
        weather = content.get("weather") or "-"
        workers = content.get("workers_present")
        workers_str = ", ".join(str(w) for w in workers) if isinstance(workers, list) and workers else (str(workers) if workers else "-")

        buf = BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=inch, leftMargin=inch, topMargin=inch, bottomMargin=inch)
        styles = getSampleStyleSheet()
        story = [
            Paragraph("Daily Site Log", styles["Heading1"]),
            Spacer(1, 12),
            Paragraph(f"Project: {project_name}  |  Date: {log_date}  |  Weather: {weather}  |  Workers: {workers_str}", styles["Normal"]),
            Spacer(1, 12),
            Paragraph("Work completed", styles["Heading2"]),
            Paragraph(work or "-", styles["Normal"]),
        ]
        if issues:
            story.append(Spacer(1, 8))
            story.append(Paragraph("Issues", styles["Heading2"]))
            story.append(Paragraph(issues, styles["Normal"]))
        doc.build(story)
        return buf.getvalue()
    except Exception:
        return _minimal_pdf_bytes_fallback()


def render_project_summary_pdf(project_name: str, content: dict[str, Any]) -> bytes:
    """Generate PDF for project summary (name, client, dates, budget, status). Uses ReportLab."""
    try:
        return _reportlab_project_summary(project_name, content)
    except Exception:
        return _minimal_pdf_bytes_fallback()


def render_test_pdf() -> bytes:
    """Return a minimal PDF with visible text for debugging (temp file path)."""
    def draw(c):
        from reportlab.lib.colors import black
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(72, 400, "Hello from Reports PDF")
        c.setFont("Helvetica", 10)
        c.drawString(72, 370, "If you see this, PDF generation works.")
        c.showPage()
    return _canvas_to_bytes(draw)


def render_daily_report_pdf(project_name: str, payload: dict[str, Any]) -> bytes:
    """Generate PDF for daily site report. Uses ReportLab (reliable on all platforms)."""
    try:
        return _reportlab_daily_report(project_name, payload)
    except Exception:
        return _minimal_pdf_bytes_fallback()


def render_weekly_report_pdf(project_name: str, payload: dict[str, Any], period_label: str) -> bytes:
    """Generate PDF for weekly site report (aggregated data). No user form — period_label e.g. '4–10 Mar 2026'."""
    try:
        return _reportlab_daily_report(
            project_name,
            payload,
            report_title="WEEKLY SITE REPORT",
            report_subtitle=period_label,
            footer_label="Weekly Site Report",
        )
    except Exception:
        return _minimal_pdf_bytes_fallback()


def render_monthly_report_pdf(project_name: str, payload: dict[str, Any], period_label: str) -> bytes:
    """Generate PDF for monthly site report (aggregated data). No user form — period_label e.g. 'March 2026'."""
    try:
        return _reportlab_daily_report(
            project_name,
            payload,
            report_title="MONTHLY SITE REPORT",
            report_subtitle=period_label,
            footer_label="Monthly Site Report",
        )
    except Exception:
        return _minimal_pdf_bytes_fallback()


def _reportlab_export_table_pdf(
    project_name: str,
    report_title: str,
    headers: list[str],
    col_widths: list[float],
    rows: list[list[Any]],
    footer_label: str,
) -> bytes:
    """Single-table export PDF (Budget or Tasks) with brand header and formatted table."""
    from reportlab.lib.colors import HexColor

    text_primary = HexColor(_PDF["text_primary"])
    text_secondary = HexColor(_PDF["text_secondary"])
    primary = HexColor(_PDF["primary"])
    white = HexColor(_PDF["white"])
    card = HexColor(_PDF["card"])
    border = HexColor(_PDF["border"])
    header_bg = HexColor(_PDF["header_bg"])
    mx = 56
    page_w, page_h = 595, 842
    bar_h = 56
    section_gap = 24

    def draw(c):
        c.setFillColor(header_bg)
        c.rect(0, page_h - bar_h, page_w, bar_h, fill=1, stroke=0)
        c.setFillColor(primary)
        c.rect(0, page_h - bar_h, page_w, 3, fill=1, stroke=0)
        _draw_brand_block(c, mx, page_h - 14, primary, white, text_primary, text_secondary, small=False)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(mx + 200, page_h - 32, report_title)
        c.setFont("Helvetica", 9)
        c.setFillColor(HexColor("#cbd5e1"))
        c.drawString(mx + 200, page_h - 46, _safe(project_name, 50))
        y = [page_h - bar_h - 32]
        c.setFillColor(primary)
        c.rect(mx, y[0] - 16, 4, 16, fill=1, stroke=0)
        c.setFillColor(text_primary)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(mx + 10, y[0] - 20, "Details")
        c.setStrokeColor(border)
        c.setLineWidth(0.25)
        c.line(mx, y[0] - 26, page_w - mx, y[0] - 26)
        y[0] -= 36
        _draw_data_table(
            c, mx, y, col_widths, headers, rows,
            row_h=20, card=card, border=border,
            text_primary=text_primary, text_secondary=text_secondary,
            page_h=page_h, min_y=70, alternate_fill=HexColor("#f8fafc"),
        )
        c.setStrokeColor(primary)
        c.setLineWidth(1)
        c.line(mx, 56, page_w - mx, 56)
        _draw_brand_block(c, mx, 42, primary, white, text_primary, text_secondary, small=True, name_color=text_primary)
        c.setFillColor(text_secondary)
        c.setFont("Helvetica", 8)
        c.drawString(mx + 118, 36, f"{_BRAND['name']} — {footer_label}")
        c.showPage()

    return _canvas_to_bytes(draw)


def render_budget_export_pdf(project_name: str, items: list[dict[str, Any]]) -> bytes:
    """Formatted Budget export PDF (category, description, estimated, actual, variance)."""
    try:
        headers = ["Category", "Description", "Est. Cost", "Actual", "Variance"]
        col_widths = [90, 200, 75, 75, 75]
        rows = []
        for x in items:
            est = float(x.get("estimated_cost") or 0)
            act = float(x.get("actual_cost") or 0)
            var = act - est
            rows.append([
                x.get("category") or "—",
                (x.get("description") or "—")[:50],
                f"{est:.2f}",
                f"{act:.2f}",
                f"{var:+.2f}",
            ])
        if not rows:
            rows = [["No budget items", "—", "—", "—", "—"]]
        return _reportlab_export_table_pdf(
            project_name, "BUDGET EXPORT", headers, col_widths, rows, "Budget Export",
        )
    except Exception:
        return _minimal_pdf_bytes_fallback()


def render_tasks_export_pdf(project_name: str, tasks: list[dict[str, Any]]) -> bytes:
    """Formatted Tasks export PDF (title, start, due, priority, status, hours)."""
    try:
        headers = ["Title", "Start", "Due", "Priority", "Status", "Est. Hrs", "Actual Hrs"]
        col_widths = [140, 72, 72, 58, 72, 52, 52]
        rows = []
        for t in tasks:
            start_s = str(t.get("start_date") or "—")[:10]
            due_s = str(t.get("due_date") or "—")[:10]
            rows.append([
                (t.get("title") or "—")[:35],
                start_s,
                due_s,
                (t.get("priority") or "—")[:8],
                (t.get("status") or "—")[:10],
                t.get("estimated_hours") if t.get("estimated_hours") is not None else "—",
                t.get("actual_hours") if t.get("actual_hours") is not None else "—",
            ])
        if not rows:
            rows = [["No tasks", "—", "—", "—", "—", "—", "—"]]
        return _reportlab_export_table_pdf(
            project_name, "TASKS EXPORT", headers, col_widths, rows, "Tasks Export",
        )
    except Exception:
        return _minimal_pdf_bytes_fallback()


# Legacy HTML/WeasyPrint helpers kept for reference; not used for PDF output by default
def _html_daily_log(project_name: str, log_date: str, content: dict[str, Any]) -> str:
    """Build HTML for daily site log (print-friendly)."""
    work = (content.get("work_completed") or "").replace("<", "&lt;").replace(">", "&gt;")
    issues = (content.get("issues") or "").replace("<", "&lt;").replace(">", "&gt;")
    weather = content.get("weather") or "-"
    workers = content.get("workers_present")
    workers_str = ", ".join(str(w) for w in workers) if isinstance(workers, list) and workers else (str(workers) if workers else "-")
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Daily Site Log - {project_name}</title></head><body><h1>Daily Site Log</h1><p>Project: {project_name} | Date: {log_date} | Weather: {weather} | Workers: {workers_str}</p><h2>Work completed</h2><p>{work or '-'}</p><h2>Issues</h2><p>{issues or '-'}</p></body></html>"""


def _html_daily_report(project_name: str, payload: dict[str, Any]) -> str:
    """Build HTML for daily site report (print-friendly)."""
    wf = payload.get("workforce") or []
    wi = payload.get("work_items") or []
    mat = payload.get("materials") or []
    iss = payload.get("issues") or []
    rows_wf = "".join(f"<tr><td>{w.get('trade','')}</td><td>{w.get('present','')}</td><td>{w.get('absent','')}</td><td>{w.get('total','')}</td></tr>" for w in wf)
    rows_wi = "".join(f"<tr><td>{w.get('task_name','')}</td><td>{w.get('location') or ''}</td><td>{w.get('boq_item') or ''}</td><td>{w.get('progress_today',0)}%</td><td>{w.get('progress_cumulative',0)}%</td></tr>" for w in wi)
    rows_mat = "".join(f"<tr><td>{m.get('item_name','')}</td><td>{m.get('quantity') or ''}</td><td>{m.get('supplier') or ''}</td><td>{m.get('status') or ''}</td></tr>" for m in mat)
    rows_iss = "".join(f"<tr><td>{i.get('issue_type') or ''}</td><td>{i.get('description','')}</td><td>{i.get('impact') or ''}</td><td>{i.get('responsible_party') or ''}</td></tr>" for i in iss)
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Daily Site Report - {project_name}</title></head><body><h1>Daily Site Report</h1><p>Project: {project_name} | Date: {payload.get('report_date','')} | Weather: {payload.get('weather') or '-'}</p><h2>Workforce</h2><table><tr><th>Trade</th><th>Present</th><th>Absent</th><th>Total</th></tr>{rows_wf or '<tr><td colspan="4">None</td></tr>'}</table><h2>Work Done Today</h2><table><tr><th>Task</th><th>Location</th><th>BOQ</th><th>Today %</th><th>Cum. %</th></tr>{rows_wi or '<tr><td colspan="5">None</td></tr>'}</table><h2>Materials</h2><table><tr><th>Item</th><th>Quantity</th><th>Supplier</th><th>Status</th></tr>{rows_mat or '<tr><td colspan="4">None</td></tr>'}</table><h2>Issues</h2><table><tr><th>Type</th><th>Description</th><th>Impact</th><th>Responsible</th></tr>{rows_iss or '<tr><td colspan="4">None</td></tr>'}</table></body></html>"""
