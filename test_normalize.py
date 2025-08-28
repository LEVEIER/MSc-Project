import os, sys, unittest
# 确保能从 Project 根导包
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from nlp.instruction_parser import normalize_place_name

class TestNormalize(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(normalize_place_name(" School "), "school")
        self.assertEqual(normalize_place_name("market"), "market")

    def test_alias_cn(self):
        # 需确保 alias_map 中有 "商场": "shoppingMall"
        self.assertEqual(normalize_place_name("商场"), "shoppingMall")

    def test_empty_none(self):
        self.assertIsNone(normalize_place_name(""))
        self.assertIsNone(normalize_place_name(None))

if __name__ == "__main__":
    unittest.main()
