import os
import sys
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

# 从 Project 根目录导包
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# 无显示环境（CI/服务器）需要
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPixmap
from ui.ui_window import VoiceInputDialog


class TestStartNavigation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def test_start_navigation_without_llm(self):
        # 让 QPixmap("Town05.png") 返回一个 10x10 的空白图（避免真实文件依赖）
        real_qpixmap = QPixmap
        def fake_qpixmap_ctor(*args, **kwargs):
            return real_qpixmap(10, 10)

        # 假 CARLA 依赖
        fake_world = SimpleNamespace(get_map=lambda: object())
        def fake_connect_to_carla():
            return object(), fake_world, object()

        fake_location = SimpleNamespace(x=0, y=0, z=0)
        # define_landmarks() 期望每个 landmark 是一个“有 .location 的对象”
        landmarks = {
            "school": SimpleNamespace(location=fake_location),
            "home":   SimpleNamespace(location=fake_location),
        }

        class FakeGRP:
            def __init__(self, *args, **kwargs):
                pass
            def trace_route(self, a, b):
                # 返回至少两个 (waypoint, option)；
                # waypoint 需要有 .transform.location
                wp = SimpleNamespace(transform=SimpleNamespace(location=fake_location))
                return [(wp, "opt"), (wp, "opt")]

        called = {"ok": False}
        def fake_run_autonomous_navigation(start_name, end_name):
            # 不真的连 CARLA；只记录被调用
            called["ok"] = True

        with patch("ui.ui_window.TEST_MODE", True), \
             patch("ui.ui_window.QPixmap", side_effect=fake_qpixmap_ctor), \
             patch.object(VoiceInputDialog, "update_map", lambda _self: None), \
             patch("ui.ui_window.connect_to_carla",  side_effect=fake_connect_to_carla), \
             patch("ui.ui_window.setup_environment", side_effect=lambda w: None), \
             patch("ui.ui_window.cleanup_actors",    side_effect=lambda w: None), \
             patch("ui.ui_window.define_landmarks",  side_effect=lambda w: landmarks), \
             patch("ui.ui_window.GlobalRoutePlanner", FakeGRP), \
             patch("ui.ui_window.run_autonomous_navigation", side_effect=fake_run_autonomous_navigation):

            dlg = VoiceInputDialog()
            dlg.start_landmark = "school"
            dlg.end_landmark   = "home"

            # 运行被测方法
            dlg.start_navigation()
            QApplication.processEvents()
            time.sleep(0.05)  # 给事件循环一点时间

            # 断言：已触发自动驾驶
            self.assertTrue(called["ok"], "run_autonomous_navigation 未被调用")

            # 断言：start_navigation 内部已把 full_route 转为 self.route（waypoint 列表）
            # 注意：由于 update_map 被 patch 掉，不影响 route 的断言
            self.assertTrue(hasattr(dlg, "route"), "self.route 未设置")
            self.assertGreaterEqual(len(dlg.route), 2, f"路线点数量不足: {len(dlg.route)}")


if __name__ == "__main__":
    unittest.main(verbosity=2, exit=False)
