import unittest

from .services import calculate_revenue


class RevenueCalculationTests(unittest.TestCase):
    def test_existing_revenue_example_and_bank_conversion(self):
        result = calculate_revenue(1000000, 200000, 30000)
        self.assertEqual(result['call_share'], 50000)
        self.assertEqual(result['message_share'], 100000)
        self.assertEqual(result['gross_earnings'], 150000)
        self.assertEqual(result['balance'], 120000)
        self.assertEqual(result['bank_payable'], 1200000)
        self.assertEqual(result['deductions'], result['previous_payments'])

    def test_empty_data_and_pending_tax(self):
        result = calculate_revenue()
        self.assertEqual(result['balance'], 0)
        self.assertIsNone(result['tax'])
        self.assertEqual(result['tax_status'], 'pending')
        self.assertEqual(result['ledger_status'], 'pending')

    def test_legacy_small_share_guard_and_truncation(self):
        for call, message, expected in [(20, 2, 0), (21, 3, 2), (39, 3, 2), (40, 4, 4)]:
            with self.subTest(call=call, message=message):
                self.assertEqual(calculate_revenue(call, message)['gross_earnings'], expected)

    def test_negative_balance_is_preserved_with_no_payable_amount(self):
        result = calculate_revenue(1000, 100, 150)
        self.assertEqual(result['balance'], -50)
        self.assertEqual(result['payable'], 0)
        self.assertEqual(result['bank_payable'], 0)

    def test_large_totals_use_exact_integer_arithmetic(self):
        result = calculate_revenue(10 ** 18 + 39, 10 ** 18 + 3)
        self.assertEqual(result['call_share'], 50000000000000001)
        self.assertEqual(result['message_share'], 500000000000000001)

    def test_negative_source_totals_follow_legacy_guard(self):
        result = calculate_revenue(-1000, -100, -10)
        self.assertEqual(result['gross_earnings'], 0)
        self.assertEqual(result['balance'], 10)
