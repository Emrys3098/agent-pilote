import unittest
from rpn import evaluate

class TestRPN(unittest.TestCase):
    def test_empty_expression(self):
        with self.assertRaises(ValueError):
            evaluate("")
    def test_missing_operand(self):
        with self.assertRaises(ValueError):
            evaluate("3 +")
    def test_extra_values(self):
        with self.assertRaises(ValueError):
            evaluate("3 4 + 5")
    def test_invalid_element(self):
        with self.assertRaises(ValueError):
            evaluate("abc")
    def test_division_by_zero(self):
        with self.assertRaises(ValueError):
            evaluate("2 0 /")
    def test_normal_evaluation(self):
        self.assertEqual(evaluate("3 4 +"), 7.0)
    def test_negative_numbers(self):
        self.assertEqual(evaluate("-2.5 3.5 +"), 1.0)
    def test_division_with_negative(self):
        self.assertEqual(evaluate("5 -2 /") , -2.5)