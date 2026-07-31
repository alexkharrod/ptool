"""
Packing-list / commercial-invoice parser for uploaded XLS and XLSX files.

Supports two common supplier layouts:
  - Packing list sheet: rows with PO#, P/N, description, cartons, qty, NW, GW, dims, CBM
  - CI sheet: rows with qty, PO#, product#, description, unit cost

Returns a dict:
    {
        "items": [
            {
                "po_number": "81300",
                "sku": "20-3008-1085",
                "description": "AD Player",
                "cartons": 20,
                "qty": 200,
                "nw_kg": "280.00",
                "gw_kg": "318.00",
                "dimensions_cm": "42×36×39.5",
                "cbm": "1.1945",
                "unit_cost_usd": "46.00",   # from CI, may be None
            },
            ...
        ],
        "totals": {
            "cartons": 328,
            "pieces": 9535,
            "nw_kg": "6962.50",
            "gw_kg": "7971.60",
            "cbm": "41.8352",
        },
        "warnings": ["Could not find CI sheet — unit costs not imported"],
    }
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any


# ── helpers ──────────────────────────────────────────────────────────────────

def _safe_dec(val, places: int = 4) -> Decimal | None:
    """Parse a value to Decimal, quantized to `places` decimal places.

    IMPORTANT: nw_kg / gw_kg on both Shipment and ShipmentItem are
    decimal_places=2. Emitting 4 d.p. here makes the formset silently
    fail validation, so callers must pass the right precision.
    """
    if val is None or val == "":
        return None
    try:
        return Decimal(str(val)).quantize(Decimal(1).scaleb(-places))
    except (InvalidOperation, ValueError):
        return None


def _dec_str(val, places: int = 4) -> str | None:
    d = _safe_dec(val, places)
    return str(d) if d is not None else None


def _safe_int(val) -> int | None:
    try:
        f = float(val)
        return int(round(f)) if f > 0 else None
    except (TypeError, ValueError):
        return None


def _norm(s: str) -> str:
    """Lowercase + collapse whitespace for fuzzy header matching."""
    return re.sub(r"\s+", " ", str(s)).strip().lower()


def _cell_str(sheet, row: int, col: int) -> str:
    try:
        return str(sheet.cell_value(row, col)).strip()
    except Exception:
        return ""


# ── sheet detectors ──────────────────────────────────────────────────────────

# Keywords we look for in header rows for each sheet type.
_PL_KEYWORDS = {"po", "p/n", "carton", "qty", "nw", "gw", "cbm"}
_CI_KEYWORDS  = {"unit cost", "unit price", "unit  cost", "单价"}


def _find_header_row(sheet, keywords: set[str], max_scan: int = 20) -> int | None:
    """Return the row index whose cells collectively contain all keywords."""
    for r in range(min(max_scan, sheet.nrows)):
        row_text = " ".join(_norm(_cell_str(sheet, r, c)) for c in range(sheet.ncols))
        if all(kw in row_text for kw in keywords):
            return r
    return None


def _col_idx(header_vals: list[str], *candidates: str) -> int | None:
    """Find the first column whose normalised header contains any candidate."""
    for candidate in candidates:
        for i, h in enumerate(header_vals):
            if candidate in _norm(h):
                return i
    return None


# ── packing list parser ───────────────────────────────────────────────────────

_TOTAL_LABELS = {"total", "totals", "grand total", "sub", "sub total", "subtotal"}

# Markers that identify a second (sub) header row rather than a data row.
_SUB_MARKERS = ("sub", "total", "/ctn", "cbm", "size", "per ctn", "pcs/ctn")


def _build_header_map(sheet, header_row: int) -> tuple[list[str], int]:
    """
    Combine the main header row with an optional sub-header row underneath it.

    Packing lists commonly use a two-row header with merged group cells:

        PO# | P/N | Cartons | Qty. (pcs)      | N.W. (kgs)      | Measurement (cm)
            |     |         | PCS/CTN | Total | N.W/CTN | Total | Size (cm) | CBM

    Merged group titles only occupy their first column, so we forward-fill the
    main row, then join it with the sub row. That gives each column an
    unambiguous label like "n.w. (kgs) total" vs "n.w. (kgs) n.w/ctn" —
    which is what lets us pick the per-line TOTAL column instead of the
    per-carton one.

    Returns (combined_headers, data_start_row).
    """
    ncols = sheet.ncols
    main = [_norm(_cell_str(sheet, header_row, c)) for c in range(ncols)]

    # Forward-fill merged group titles across blank cells
    filled: list[str] = []
    last = ""
    for h in main:
        if h:
            last = h
        filled.append(last if h == "" else h)

    sub_row = header_row + 1
    has_sub = False
    sub: list[str] = [""] * ncols
    if sub_row < sheet.nrows:
        candidate = [_norm(_cell_str(sheet, sub_row, c)) for c in range(ncols)]
        hits = sum(1 for h in candidate if any(m in h for m in _SUB_MARKERS))
        if hits >= 2:
            has_sub = True
            sub = candidate

    combined = [f"{filled[c]} {sub[c]}".strip() for c in range(ncols)]
    data_start = sub_row + 1 if has_sub else header_row + 1
    return combined, data_start


def _pick_col(headers: list[str], must: tuple[str, ...],
              prefer: tuple[str, ...] = (), exclude: tuple[str, ...] = ()) -> int | None:
    """
    Choose a column whose combined header contains any term in `must`.

    If several match, one containing a `prefer` term wins (e.g. the "total"
    column over the "/ctn" column). Columns matching `exclude` are skipped.
    """
    candidates = [
        i for i, h in enumerate(headers)
        if any(m in h for m in must) and not any(x in h for x in exclude)
    ]
    if not candidates:
        return None
    for i in candidates:
        if any(p in headers[i] for p in prefer):
            return i
    return candidates[0]


def _parse_pl_sheet(sheet) -> tuple[list[dict], dict, list[str]]:
    """
    Return (items, totals, warnings) from a packing-list-style sheet.

    Items contain everything except unit_cost_usd (filled later from CI).
    Totals come from the summary row (labelled "TOTAL" or with a blank PO#).
    """
    warnings: list[str] = []

    header_row = _find_header_row(sheet, {"po", "carton", "qty"})
    if header_row is None:
        warnings.append("Could not locate packing list header row.")
        return [], {}, warnings

    hdrs, data_start = _build_header_map(sheet, header_row)

    col_po   = _pick_col(hdrs, ("po#", "po #", "po"))
    col_pn   = _pick_col(hdrs, ("p/n", "item no", "product no", "sku", "pn"))
    col_desc = _pick_col(hdrs, ("description", "product desc", "desc"))
    col_ctn  = _pick_col(hdrs, ("carton", "ctns"), exclude=("/ctn", "pcs/ctn"))
    # Prefer the per-line TOTAL column over the per-carton column
    col_qty  = _pick_col(hdrs, ("qty", "pcs", "quantity"),
                         prefer=("total", "sub"), exclude=("carton",))
    col_nw   = _pick_col(hdrs, ("n.w", "nw"), prefer=("total", "sub"))
    col_gw   = _pick_col(hdrs, ("g.w", "gw"), prefer=("total", "sub"))
    col_cbm  = _pick_col(hdrs, ("cbm",))
    col_dims = _pick_col(hdrs, ("size", "measurement", "dimension", "meas"),
                         exclude=("cbm",))

    items: list[dict] = []
    totals: dict = {}

    for r in range(data_start, sheet.nrows):
        row_vals = [_cell_str(sheet, r, c) for c in range(sheet.ncols)]
        if not any(v.strip() for v in row_vals):
            continue

        po_val  = row_vals[col_po].strip()  if col_po  is not None else ""
        pn_val  = row_vals[col_pn].strip()  if col_pn  is not None else ""
        ctn_val = row_vals[col_ctn].strip() if col_ctn is not None else ""

        # ── Totals row: PO cell says "TOTAL" (or is blank) + a carton count ──
        if _norm(po_val) in _TOTAL_LABELS or (not po_val and ctn_val):
            tot_ctns = _safe_int(ctn_val)
            if tot_ctns and tot_ctns > 1:
                totals["cartons"] = tot_ctns
                if col_qty is not None:
                    totals["pieces"] = _safe_int(row_vals[col_qty])
                if col_nw is not None:
                    totals["nw_kg"] = _safe_dec(row_vals[col_nw], 2)
                if col_gw is not None:
                    totals["gw_kg"] = _safe_dec(row_vals[col_gw], 2)
                if col_cbm is not None:
                    totals["cbm"] = _safe_dec(row_vals[col_cbm], 4)
            continue

        # ── Skip pallet-summary lines, "Notes:", bullets and other prose ─────
        # These land in the PO# column and blow past its 50-char DB limit,
        # which would otherwise fail formset validation with no visible error.
        if not pn_val and not ctn_val:
            continue
        if len(po_val) > 50 or po_val.startswith(("•", "-", "*")):
            continue

        items.append({
            "po_number":     po_val,
            "sku":           pn_val,
            "description":   (row_vals[col_desc].strip() if col_desc is not None else "")[:200],
            "cartons":       _safe_int(ctn_val),
            "qty":           _safe_int(row_vals[col_qty]) if col_qty is not None else None,
            # 2 d.p. — matches ShipmentItem.nw_kg / gw_kg
            "nw_kg":         _dec_str(row_vals[col_nw], 2) if col_nw is not None else None,
            "gw_kg":         _dec_str(row_vals[col_gw], 2) if col_gw is not None else None,
            "cbm":           _dec_str(row_vals[col_cbm], 4) if col_cbm is not None else None,
            "dimensions_cm": (row_vals[col_dims].replace("*", "×").strip()[:50]
                              if col_dims is not None else ""),
            "unit_cost_usd": None,
        })

    if not items:
        warnings.append("Packing list sheet found but no data rows extracted.")

    # ── Fall back to summing line items if no totals row was found ───────────
    if items and not totals:
        totals["cartons"] = sum(i["cartons"] or 0 for i in items) or None
        totals["pieces"]  = sum(i["qty"] or 0 for i in items) or None
        for key in ("nw_kg", "gw_kg", "cbm"):
            vals = [Decimal(i[key]) for i in items if i.get(key)]
            if vals:
                totals[key] = sum(vals).quantize(Decimal("0.0001") if key == "cbm" else Decimal("0.01"))
        warnings.append("No totals row found — totals calculated by summing line items.")

    return items, totals, warnings


# ── CI parser ─────────────────────────────────────────────────────────────────

def _parse_ci_sheet(sheet) -> tuple[dict[tuple[str, str], Decimal], list[str]]:
    """
    Return ({(po_number, sku): unit_cost}, warnings) from a CI-style sheet.
    """
    warnings: list[str] = []

    header_row = _find_header_row(sheet, {"unit cost"})
    if header_row is None:
        # Try alternate keywords
        header_row = _find_header_row(sheet, {"unit price"})
    if header_row is None:
        warnings.append("Could not locate CI header row — unit costs not imported.")
        return {}, warnings

    hdrs = [_cell_str(sheet, header_row, c) for c in range(sheet.ncols)]
    col_po   = _col_idx(hdrs, "po#", "po #", "po")
    col_pn   = _col_idx(hdrs, "product no", "p/n", "item no", "sku")
    col_cost = _col_idx(hdrs, "unit cost", "unit price", "单价")

    if col_cost is None:
        warnings.append("Unit cost column not found in CI sheet.")
        return {}, warnings

    costs: dict[tuple[str, str], Decimal] = {}
    for r in range(header_row + 1, sheet.nrows):
        po  = _cell_str(sheet, r, col_po)  if col_po  is not None else ""
        pn  = _cell_str(sheet, r, col_pn)  if col_pn  is not None else ""
        raw = _cell_str(sheet, r, col_cost) if col_cost is not None else ""
        cost = _safe_dec(raw)
        if cost and (po or pn):
            costs[(po.strip(), pn.strip())] = cost

    return costs, warnings


# ── sheet classifier ──────────────────────────────────────────────────────────

def _classify_sheets(wb) -> tuple[Any | None, Any | None]:
    """Return (pl_sheet, ci_sheet) or None for each if not found."""
    pl_sheet = ci_sheet = None

    for name in wb.sheet_names():
        sh = wb.sheet_by_name(name)
        # Look at first 20 rows for keywords
        text = " ".join(
            _norm(_cell_str(sh, r, c))
            for r in range(min(20, sh.nrows))
            for c in range(sh.ncols)
        )
        has_pl = all(kw in text for kw in {"po", "carton", "qty", "cbm"})
        has_ci = any(kw in text for kw in {"unit cost", "unit price"}) and "po" in text

        if has_pl and pl_sheet is None:
            pl_sheet = sh
        if has_ci and ci_sheet is None:
            ci_sheet = sh

    return pl_sheet, ci_sheet


# ── public entry point ────────────────────────────────────────────────────────

def parse_shipment_doc(file_obj) -> dict:
    """
    Parse an uploaded file object (XLS or XLSX) and return structured shipment data.

    Accepts Django InMemoryUploadedFile / TemporaryUploadedFile.
    """
    import io

    warnings: list[str] = []

    # Read raw bytes
    file_obj.seek(0)
    raw = file_obj.read()
    filename = getattr(file_obj, "name", "").lower()

    # Try XLSX first, fall back to XLS
    wb = None
    if filename.endswith(".xlsx"):
        try:
            import openpyxl
            wb_xl = openpyxl.load_workbook(io.BytesIO(raw), data_only=True)

            # Wrap openpyxl into an xlrd-like interface
            class _XlSheet:
                def __init__(self, ws):
                    self._ws = ws
                    self.nrows = ws.max_row or 0
                    self.ncols = ws.max_column or 0
                def cell_value(self, r, c):
                    v = self._ws.cell(row=r + 1, column=c + 1).value
                    return "" if v is None else v

            class _XlWb:
                def __init__(self, wb):
                    self._wb = wb
                def sheet_names(self):
                    return self._wb.sheetnames
                def sheet_by_name(self, name):
                    return _XlSheet(self._wb[name])

            wb = _XlWb(wb_xl)
        except ImportError:
            warnings.append("openpyxl not installed — trying xlrd for .xlsx.")

    if wb is None:
        try:
            import xlrd
            wb = xlrd.open_workbook(file_contents=raw)
        except Exception as e:
            return {"items": [], "totals": {}, "warnings": [f"Could not open file: {e}"]}

    pl_sheet, ci_sheet = _classify_sheets(wb)

    if pl_sheet is None:
        return {"items": [], "totals": {}, "warnings": ["No packing list sheet detected in this file."]}

    items, totals, pl_warnings = _parse_pl_sheet(pl_sheet)
    warnings.extend(pl_warnings)

    # Merge CI unit costs
    if ci_sheet is not None:
        costs, ci_warnings = _parse_ci_sheet(ci_sheet)
        warnings.extend(ci_warnings)
        for item in items:
            key = (item["po_number"], item["sku"])
            if key in costs:
                item["unit_cost_usd"] = str(costs[key])
            elif ("", item["sku"]) in costs:
                item["unit_cost_usd"] = str(costs[("", item["sku"])])
    else:
        warnings.append("No commercial invoice sheet detected — unit costs not imported.")

    # Convert Decimal totals to strings for JSON
    # nw_kg and gw_kg are 2 d.p. fields; cbm is 4 d.p.
    _dp = {"nw_kg": Decimal("0.01"), "gw_kg": Decimal("0.01"), "cbm": Decimal("0.0001")}
    totals_out = {}
    for k, v in totals.items():
        if isinstance(v, Decimal):
            totals_out[k] = str(v.quantize(_dp.get(k, Decimal("0.01"))))
        else:
            totals_out[k] = v

    # Unique PO numbers, in first-seen order, for the Shipment.po_numbers field
    po_numbers: list[str] = []
    for item in items:
        po = (item.get("po_number") or "").strip()
        if po and po not in po_numbers:
            po_numbers.append(po)

    return {
        "items": items,
        "totals": totals_out,
        "po_numbers": ", ".join(po_numbers)[:200],
        "warnings": warnings,
    }
