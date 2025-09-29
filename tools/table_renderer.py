"""Reusable HTML table renderer for WiFi records.

Provides render_html_table(records, title=None) -> str which returns a complete
HTML document (utf-8) with embedded CSS optimized for long tables: sticky
header, zebra stripes, responsive layout and scrollable body so it can handle
many rows comfortably.

The function accepts a list of dicts or a pandas.DataFrame-like object.
"""
from typing import Any, Iterable, List, Optional


def _safe_str(v: Any) -> str:
    if v is None:
        return ""
    return str(v)


def render_html_table(records: Iterable, title: Optional[str] = None, columns: Optional[List[str]] = None) -> str:
    """Render records as a full HTML page with a styled table.

    Args:
        records: iterable of dict-like objects or rows (e.g., list[dict])
        title: optional page/title text
        columns: optional list specifying column order; if omitted the renderer
            will infer columns from common keys and preserve a friendly order.

    Returns:
        str: HTML document (utf-8)
    """
    # Convert to list for multiple passes
    rows = list(records)

    # Determine column order
    preferred = ["bssid", "ssid", "rssi", "frequency", "timestamp", "channel_bandwidth", "capabilities", "pavilion", "password"]
    if columns:
        cols = columns
    else:
        # gather all keys
        keys = []
        for r in rows:
            if isinstance(r, dict):
                for k in r.keys():
                    if k not in keys:
                        keys.append(k)
        # start with preferred order then append remaining
        cols = [c for c in preferred if c in keys]
        cols += [c for c in keys if c not in cols]

    # Header text
    page_title = title or "Table"

    # Build HTML
    css = """
    :root{--bg:#f7fafc;--card:#ffffff;--muted:#6b7280;--accent:#2563eb;--stripe:#f3f4f6}
    html,body{height:100%;margin:0;font-family:Inter,Segoe UI,Roboto,Arial,sans-serif;background:var(--bg);color:#0f172a}
    .page{padding:20px;max-width:1200px;margin:20px auto}
    .card{background:var(--card);border-radius:12px;box-shadow:0 6px 18px rgba(2,6,23,.08);padding:14px;}
    h1{margin:0 0 10px 0;font-size:18px;color:var(--accent)}
    .meta{font-size:13px;color:var(--muted);margin-bottom:10px}
    .table-wrap{overflow:auto;max-height:70vh;border-radius:8px;border:1px solid #e6eef8}
    table{border-collapse:collapse;width:100%;min-width:680px}
    thead th{position:sticky;top:0;background:linear-gradient(180deg,#fff,#fbfdff);padding:10px 12px;text-align:left;font-weight:600;border-bottom:1px solid #e6eef8}
    tbody td{padding:10px 12px;border-bottom:1px dashed #eef2ff;font-size:13px}
    tbody tr:nth-child(odd){background:var(--stripe)}
    tbody tr:hover{background:#eef2ff}
    .caption{font-size:13px;color:var(--muted);margin-bottom:8px}
    @media (max-width:640px){thead th,tbody td{padding:8px 6px;font-size:12px}}
    """

    head = f"""
    <!doctype html>
    <html lang="ru">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width,initial-scale=1" />
      <title>{page_title}</title>
      <style>{css}</style>
    </head>
    <body>
      <div class="page">
        <div class="card">
          <h1>{page_title}</h1>
          <div class="meta">Записей: {len(rows)}</div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
    """

    # header cells
    header_cells = "\n".join([f"<th>{c}</th>" for c in cols])

    mid = f"""
                {header_cells}
                </tr>
              </thead>
              <tbody>
    """

    # rows
    body_rows = []
    for r in rows:
        cells = []
        for c in cols:
            val = ""
            if isinstance(r, dict):
                val = _safe_str(r.get(c, ""))
            else:
                # try attribute/sequence access otherwise
                try:
                    val = _safe_str(getattr(r, c))
                except Exception:
                    try:
                        val = _safe_str(r[c])
                    except Exception:
                        val = ""
            # escape minimal HTML
            val = (val.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;"))
            cells.append(f"<td title=\"{val}\">{val}</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")

    tail = """
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </body>
    </html>
    """

    html = head + mid + "\n".join(body_rows) + tail
    return html
