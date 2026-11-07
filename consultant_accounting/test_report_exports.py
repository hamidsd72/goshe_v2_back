from io import BytesIO
import unittest
from xml.etree import ElementTree
from zipfile import ZipFile

from .report_exports import project_report, render_print_html, render_xlsx


class ReportExportTests(unittest.TestCase):
    def setUp(self):
        self.row = {'first_name': 'زهرا', 'last_name': 'حسین پور', 'phone': '09120000000',
                    'call_share': 50000, 'message_share': 100000, 'gross_earnings': 150000,
                    'opening_balance': 0, 'tax': None, 'deductions': 30000,
                    'paid_in_period': 30000, 'balance': 120000}
        self.report = project_report('performance', {'results': [self.row]},
                                     start='2026-11-01', end='2026-11-07')

    def test_xlsx_has_valid_xml_rtl_numeric_amounts_and_blank_tax(self):
        with ZipFile(BytesIO(render_xlsx(self.report))) as archive:
            for name in archive.namelist():
                ElementTree.fromstring(archive.read(name))
            namespace = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            sheet = ElementTree.fromstring(archive.read('xl/worksheets/sheet1.xml'))
            self.assertEqual(sheet.find('m:sheetViews/m:sheetView', namespace).get('rightToLeft'), '1')
            self.assertEqual(sheet.find('.//m:c[@r="D2"]/m:v', namespace).text, '50000')
            self.assertIsNone(sheet.find('.//m:c[@r="H2"]/m:v', namespace))
            self.assertEqual(sheet.find('.//m:c[@r="C2"]/m:is/m:t', namespace).text, '09120000000')

    def test_excel_strings_cannot_become_formulas(self):
        self.report['rows'][0]['first_name'] = '=HYPERLINK("https://example.com")'
        with ZipFile(BytesIO(render_xlsx(self.report))) as archive:
            sheet = ElementTree.fromstring(archive.read('xl/worksheets/sheet1.xml'))
            namespace = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            self.assertEqual(sheet.find('.//m:c[@r="A2"]', namespace).get('t'), 'inlineStr')
            self.assertEqual(sheet.findall('.//m:f', namespace), [])

    def test_print_escapes_untrusted_content_and_repeats_table_header(self):
        self.report['rows'][0]['first_name'] = '<script>alert(1)</script>'
        html = render_print_html(self.report)
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('dir="rtl"', html)
        self.assertIn('table-header-group', html)
        self.assertIn('A3 landscape', html)
        self.assertIn('120,000', html)

    def test_debt_report_excludes_zero_and_negative_balances(self):
        source = {'results': [self.row, dict(self.row, balance=0), dict(self.row, balance=-500)]}
        report = project_report('balances', source)
        self.assertEqual(len(report['rows']), 1)
        self.assertEqual(report['summary'][-1]['amount'], 120000)

    def test_settlements_include_signed_reversal_amount(self):
        events = [{'amount_toman': 30000}, {'amount_toman': -10000}]
        report = project_report('settlements', {'results': []}, events)
        self.assertEqual(report['summary'][0]['amount'], 20000)

    def test_empty_print_and_deductions_keep_tax_pending(self):
        report = project_report('deductions', {'results': []})
        self.assertEqual(report['tax_status'], 'pending')
        self.assertIn('رکوردی یافت نشد', render_print_html(report))

    def test_illegal_xml_characters_are_removed(self):
        self.report['rows'][0]['first_name'] = 'Test\x00\x01Name'
        with ZipFile(BytesIO(render_xlsx(self.report))) as archive:
            ElementTree.fromstring(archive.read('xl/worksheets/sheet1.xml'))
