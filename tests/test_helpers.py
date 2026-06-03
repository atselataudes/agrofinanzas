import unittest
from src.utils.helpers import float_to_cents, cents_to_float, format_currency

class TestHelpers(unittest.TestCase):
    def test_float_to_cents(self):
        self.assertEqual(float_to_cents(100.50), 10050)
        self.assertEqual(float_to_cents(0), 0)
        self.assertEqual(float_to_cents(None), 0)
        self.assertEqual(float_to_cents(10.05), 1005)

    def test_cents_to_float(self):
        self.assertEqual(cents_to_float(10050), 100.50)
        self.assertEqual(cents_to_float(0), 0.0)
        self.assertEqual(cents_to_float(None), 0.0)
        self.assertEqual(cents_to_float(1005), 10.05)

    def test_format_currency(self):
        self.assertEqual(format_currency(1234.56), "$1,234.56")
        self.assertEqual(format_currency(0), "$0.00")
        self.assertEqual(format_currency(None), "$0.00")

if __name__ == '__main__':
    unittest.main()
