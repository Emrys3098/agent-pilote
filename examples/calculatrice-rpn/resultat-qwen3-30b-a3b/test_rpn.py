import unittest
from unittest.mock import patch
from io import StringIO
from contextlib import redirect_stdout
import sys
import rpn

class TestRPN(unittest.TestCase):
    def test_evaluate_valid(self):
        self.assertEqual(rpn.evaluate("3 4 +"), 7.0)
        self.assertEqual(rpn.evaluate("5 2 *"), 10.0)
        self.assertEqual(rpn.evaluate("10 2 /"), 5.0)
        self.assertEqual(rpn.evaluate("2.5 3.5 +"), 6.0)

    def test_evaluate_empty(self):
        with self.assertRaises(ValueError) as cm:
            rpn.evaluate("")
        self.assertEqual(str(cm.exception), "Empty expression")

    def test_evaluate_insufficient_operands(self):
        with self.assertRaises(ValueError) as cm:
            rpn.evaluate("3 +")
        self.assertEqual(str(cm.exception), "Insufficient operands")

    def test_evaluate_unknown_token(self):
        with self.assertRaises(ValueError) as cm:
            rpn.evaluate("3 x +")
        self.assertEqual(str(cm.exception), "Unknown token 'x'")

    def test_evaluate_division_by_zero(self):
        with self.assertRaises(ValueError) as cm:
            rpn.evaluate("5 0 /")
        self.assertEqual(str(cm.exception), "Division by zero")

    def test_evaluate_multiple_values(self):
        with self.assertRaises(ValueError) as cm:
            rpn.evaluate("3 4")
        self.assertEqual(str(cm.exception), "Multiple values left at end")

    def test_cli_valid(self):
        with patch('sys.argv', ['rpn.py', '3 4 +']):
            with StringIO() as buf, redirect_stdout(buf):
                rpn.main()
                output = buf.getvalue().strip()
            self.assertEqual(output, '7.0')

    def test_cli_invalid(self):
        with patch('sys.argv', ['rpn.py', '3 +']):
            with StringIO() as buf, redirect_stdout(buf):
                with self.assertRaises(SystemExit) as cm:
                    rpn.main()
                self.assertEqual(cm.exception.code, 1)
                output = buf.getvalue().strip()
            self.assertEqual(output, "Erreur : Insufficient operands")

if __name__ == '__main__':
    unittest.main(argv=[''], exit=False)