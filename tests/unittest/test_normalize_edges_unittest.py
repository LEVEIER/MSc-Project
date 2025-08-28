import os, sys, unittest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from nlp.instruction_parser import normalize_place_name

class TestNormalizeEdges(unittest.TestCase):
    def test_case_and_spaces(self):
        self.assertEqual(normalize_place_name("  School  "), "school")
        self.assertEqual(normalize_place_name("SCHOOL"), "school")

    def test_chinese_alias(self):
        # 需在 alias_map 中配置 "商场": "shoppingMall"
        self.assertEqual(normalize_place_name("商场"), "shoppingMall")

    def test_fullwidth_spaces(self):
        s = u"　school　"  # 全角空格
        self.assertEqual(normalize_place_name(s), "school")

    def test_unknown_place(self):
        # 未知地名：按实现会返回 lowercase 的原词
        self.assertEqual(normalize_place_name("MyDorm"), "mydorm")

    def test_empty_and_none(self):
        self.assertIsNone(normalize_place_name(""))
        self.assertIsNone(normalize_place_name(None))

if __name__ == "__main__":
    unittest.main(verbosity=2, exit=False)
