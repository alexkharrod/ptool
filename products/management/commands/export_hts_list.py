"""
Management command: export_hts_list

Exports all products with their HTS code and duty rates to Excel for accounting.
Columns: SKU, Product Name, HTS Code, Duty %, Section 301 %, Extra Tariff %

Usage:
    python manage.py export_hts_list
    python manage.py export_hts_list --output hts_list.xlsx
"""

import os

from django.core.management.base import BaseCommand

from products.models import Product


class Command(BaseCommand):
    help = "Export all products with HTS codes and duty rates to Excel for accounting"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output", default="hts_list.xlsx",
            help="Output filename (default: hts_list.xlsx)",
        )

    def handle(self, *args, **options):
        try:
            import openpyxl
            from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
        except ImportError:
            self.stderr.write(self.style.ERROR("openpyxl not installed. Run: pip install openpyxl"))
            return

        output_path = options["output"]

        products = (
            Product.objects
            .select_related("hts_code")
            .order_by("sku")
            .values("sku", "name", "hts_code__code",
                    "hts_code__duty_percent", "hts_code__section_301_percent",
                    "hts_code__extra_tariff_percent")
        )
        total = products.count()
        self.stdout.write(f"Exporting {total} products...")

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "HTS Export"

        header_fill = PatternFill("solid", start_color="1F4E79", end_color="1F4E79")
        header_font = Font(name="Arial", bold=True, color="FFFFFF", size=11)
        data_font   = Font(name="Arial", size=10)
        bold_font   = Font(name="Arial", size=10, bold=True)
        center      = Alignment(horizontal="center", vertical="center")
        left        = Alignment(horizontal="left",   vertical="center")
        thin_bottom = Border(bottom=Side(style="thin", color="D9D9D9"))
        alt_fill    = PatternFill("solid", start_color="F2F7FB", end_color="F2F7FB")
        pct_num     = '0.00"%"'

        headers    = ["SKU", "Product Name", "HTS Code", "Duty %", "Section 301 %", "Extra Tariff %"]
        col_widths = [14,    52,              18,          10,        14,               14]

        for col_idx, (h, w) in enumerate(zip(headers, col_widths), start=1):
            cell = ws.cell(row=1, column=col_idx, value=h)
            cell.font      = header_font
            cell.fill      = header_fill
            cell.alignment = center
            ws.column_dimensions[cell.column_letter].width = w

        ws.row_dimensions[1].height = 22
        ws.freeze_panes = "A2"

        for row_idx, p in enumerate(products, start=2):
            fill = alt_fill if row_idx % 2 == 0 else None

            def c(col, value, align=center, font=data_font, num_format=None):
                cell = ws.cell(row=row_idx, column=col, value=value)
                cell.font      = font
                cell.alignment = align
                cell.border    = thin_bottom
                if fill:
                    cell.fill = fill
                if num_format:
                    cell.number_format = num_format
                return cell

            c(1, p["sku"],                                           font=bold_font)
            c(2, p["name"],                                          align=left)
            c(3, p["hts_code__code"] or "")
            c(4, float(p["hts_code__duty_percent"] or 0),            num_format=pct_num)
            c(5, float(p["hts_code__section_301_percent"] or 0),     num_format=pct_num)
            c(6, float(p["hts_code__extra_tariff_percent"] or 0),    num_format=pct_num)

            ws.row_dimensions[row_idx].height = 16

        ws.auto_filter.ref = f"A1:F{total + 1}"

        wb.save(output_path)
        self.stdout.write(self.style.SUCCESS(
            f"\n✓ Saved: {os.path.abspath(output_path)}\n  {total} products exported"
        ))
