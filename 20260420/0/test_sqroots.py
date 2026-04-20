import unittest
import fun_1


class TestSqroots(unittest.TestCase):
    def test_sqroots_1(self):
        self.assertEqual(fun_1.sqroots("1 2 1"), "-1.0")

    def test_sqroots_2(self):
        self.assertEqual(fun_1.sqroots("1 0 -1"), "-1.0 1.0")
    
    def test_sqroots_no_roots(self):
        self.assertEqual(fun_1.sqroots("1 1 1"), "")

    def test_sqroots_a_zero_error(self):
        with self.assertRaises(ValueError):
            fun_1.sqroots("0 2 1")
        
    def test_sqroots_invalid_coeffs_error(self):
        with self.assertRaises(ValueError):
            fun_1.sqroots("1 2")
