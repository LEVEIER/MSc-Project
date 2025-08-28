import os, sys, unittest, re
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

def simple_regex_parse(t: str):
    if not t:
        return {"start":"", "end":""}
    m = re.search(r'from\s+(\w+)\s+to\s+(\w+)', t, re.I)
    if m: return {"start": m.group(1), "end": m.group(2)}
    m = re.search(r'从\s*(\w+)\s*到\s*(\w+)', t)
    if m: return {"start": m.group(1), "end": m.group(2)}
    return {"start":"", "end":""}

class TestVoiceParseBaseline(unittest.TestCase):
    def test_english_from_to(self):
        self.assertEqual(simple_regex_parse("from school to home"),
                         {"start":"school","end":"home"})

    def test_chinese_from_to(self):
        self.assertEqual(simple_regex_parse("从school到market"),
                         {"start":"school","end":"market"})

    def test_invalid(self):
        self.assertEqual(simple_regex_parse("我想出去玩"),
                         {"start":"", "end":""})

if __name__ == "__main__":
    unittest.main()

