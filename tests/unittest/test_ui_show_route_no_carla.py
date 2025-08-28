import os
import sys
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

# 从 Project 根目录导包
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPixmap
from ui.ui_window import VoiceInputDialog


class TestShowRoute(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def test_show_route_unittest(self):
        # 让 QPixmap("Town05.png") 返回一个 10x10 的空白图（避免真实文件依赖）
        real_qpixmap = QPixmap
        def fake_qpixmap_ctor(*args, **kwargs):
            return real_qpixmap(10, 10)

        # 构造假的 CARLA 依赖
        fake_world = SimpleNamespace(get_map=lambda: object())
        def fake_connect():
            return object(), fake_world, object()

        # define_landmarks() 期望返回“有 .location 的对象”
        fake_location = SimpleNamespace(x=0, y=0, z=0)
        landmarks = {
            "school": SimpleNamespace(location=fake_location),
            "home":   SimpleNamespace(location=fake_location),
        }

        class FakeGRP:
            def __init__(self, *args, **kwargs): pass
            def trace_route(self, a, b):
                # 返回至少两个 (waypoint, option)，且 waypoint 有 .transform.location
                wp = SimpleNamespace(transform=SimpleNamespace(location=fake_location))
                return [(wp, "opt"), (wp, "opt"), (wp, "opt")]

        with patch("ui.ui_window.TEST_MODE", True), \
             patch("ui.ui_window.QPixmap", side_effect=fake_qpixmap_ctor), \
             patch.object(VoiceInputDialog, "update_map", lambda _self: None), \
             patch("ui.ui_window.connect_to_carla",  side_effect=fake_connect), \
             patch("ui.ui_window.setup_environment", side_effect=lambda w: None), \
             patch("ui.ui_window.cleanup_actors",    side_effect=lambda w: None), \
             patch("ui.ui_window.define_landmarks",  side_effect=lambda w: landmarks), \
             patch("ui.ui_window.GlobalRoutePlanner", FakeGRP):

            dlg = VoiceInputDialog()
            dlg.start_landmark = "school"
            dlg.end_landmark   = "home"

            # 调用被测方法
            dlg.show_route()
            QApplication.processEvents()
            time.sleep(0.05)

            # 断言：self.route 已经转成纯 waypoint 列表且长度 >= 2
            self.assertTrue(hasattr(dlg, "route"), "self.route 未设置")
            self.assertGreaterEqual(len(dlg.route), 2, f"路线点数量不足: {len(dlg.route)}")


if __name__ == "__main__":
    unittest.main(verbosity=2, exit=False)
