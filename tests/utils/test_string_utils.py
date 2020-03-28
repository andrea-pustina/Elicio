import unittest
import src.utils.string_utils as string_utils


class TestStringUtils(unittest.TestCase):
    def test_clean_string(self):
        s1 = "  Scree\"n saver 'Discovering\ Dengue/ Drugs â Together    "
        s2 = "Screen saver Discovering Dengue Drugs Together"
        self.assertEqual(string_utils.clean_string(s1), s2)

    def test_compare_string(self):
        s1 = "job"
        s2 = "Job"
        res = string_utils.compare_string(s1, s2)
        self.assertTrue(res, '{} -> "{}" - "{}"'.format(res, s1, s2))

        s1 = "job"
        s2 = "job job"
        res = string_utils.compare_string(s1, s2)
        self.assertFalse(res, '{} -> "{}" - "{}"'.format(res, s1, s2))

        s1 = "Pulp Fiction (m0yb4k0c)"
        s2 = "Pulp Fiction"
        res = string_utils.compare_string(s1, s2)
        self.assertTrue(res,'{} -> "{}" - "{}"'.format(res, s1, s2))

        s1 = "yins restaurant"
        s2 = "restaurant"
        res = string_utils.compare_string(s1, s2)
        self.assertFalse(res, '{} -> "{}" - "{}"'.format(res, s1, s2))

        s1 = "yins restaurant"
        s2 = "restaurant"
        res = string_utils.compare_string(s1, s2)
        #self.assertTrue(res, '{} -> "{}" - "{}"'.format(res, s1, s2))


if __name__ == '__main__':
    unittest.main()
