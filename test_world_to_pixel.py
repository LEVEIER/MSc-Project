import os, sys, unittest
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from ui.ui_window import world_to_pixel, MAP_ORIGIN, SCALE
from types import SimpleNamespace

class TestWorldToPixel(unittest.TestCase):
    def test_origin_is_0_0(self):
        loc = SimpleNamespace(x=MAP_ORIGIN[0], y=MAP_ORIGIN[1])
        x, y = world_to_pixel(loc, MAP_ORIGIN, SCALE)
        self.assertEqual((x, y), (0, 0))

    def test_x_increases_to_right(self):
        loc = SimpleNamespace(x=MAP_ORIGIN[0] + 10, y=MAP_ORIGIN[1])
        x, _ = world_to_pixel(loc, MAP_ORIGIN, SCALE)
        self.assertGreater(x, 0)

    def test_y_direction_expectation(self):
        # 按你当前实现：y = (origin[1] - location.y) * scale
        # 当 location.y < origin[1]，y 应该 > 0
        loc = SimpleNamespace(x=MAP_ORIGIN[0], y=MAP_ORIGIN[1] - 10)
        _, y = world_to_pixel(loc, MAP_ORIGIN, SCALE)
        self.assertGreater(y, 0)

if __name__ == "__main__":
    unittest.main()
