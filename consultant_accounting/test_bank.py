import unittest

from .bank import bank_row, render_bank_file, valid_iranian_iban


class BankFileTests(unittest.TestCase):
    def setUp(self):
        self.row = {'user_id': 1, 'iban': 'IR760140040004110176408212',
                    'first_name': 'زهرا', 'last_name': 'حسین پور', 'balance': 200000}

    def test_sample_format_and_trailing_comma(self):
        row = bank_row(self.row, 200000)
        self.assertEqual(row['errors'], [])
        self.assertEqual(render_bank_file([row]),
                         'IR760140040004110176408212,2000000,زهرا,حسین پور,حقوق,\r\n'.encode('utf-8'))

    def test_iban_checksum_country_and_length(self):
        self.assertTrue(valid_iranian_iban(' ir76 0140040004110176408212 '))
        for value in ('', 'IR000140040004110176408212', 'GB760140040004110176408212',
                      'IR76014004000411017640821', 'IR۷۶۰۱۴۰۰۴۰۰۰۴۱۱۰۱۷۶۴۰۸۲۱۲'):
            self.assertFalse(valid_iranian_iban(value))

    def test_current_balance_caps_historical_amount(self):
        self.assertEqual(bank_row(self.row, 10)['amount_rial'], 100)
        for balance in (0, -1):
            self.assertTrue(bank_row(self.row, balance)['errors'])

    def test_ambiguous_iban_and_invalid_names_are_excluded(self):
        self.assertTrue(bank_row(dict(self.row, iban_ambiguous=True), 100)['errors'])
        for value in ('', 'نام,دوم', 'نام\nدوم', 'نام\rدوم'):
            self.assertTrue(bank_row(dict(self.row, first_name=value), 100)['errors'])

    def test_multiple_rows_and_invalid_file(self):
        row = bank_row(self.row, 100)
        self.assertEqual(render_bank_file([row, row]).count(b'\r\n'), 2)
        with self.assertRaises(ValueError):
            render_bank_file([])
        with self.assertRaises(ValueError):
            render_bank_file([bank_row(self.row, 0)])
