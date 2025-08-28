import os, sys, time, unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPixmap
from ui.ui_window import VoiceInputDialog

class TestVoiceDialogErrors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def _fake_pixmap(self, *args, **kwargs):
        # 避免加载真实图片
        return QPixmap(10, 10)

    def test_invalid_landmarks(self):
        fake_world = SimpleNamespace(get_map=lambda: object())
        def fake_connect(): return object(), fake_world, object()

        # define_landmarks 不含目标键
        landmarks = {"home": SimpleNamespace(location=SimpleNamespace(x=0,y=0,z=0))}

        class FakeGRP:
            def __init__(self, *a, **k): pass
            def trace_route(self, a, b):  # 不会被调用
                self.fail("trace_route should not be called for invalid landmarks")

        with patch("ui.ui_window.TEST_MODE", True), \
             patch("ui.ui_window.QPixmap", side_effect=self._fake_pixmap), \
             patch.object(VoiceInputDialog, "update_map", lambda _s: None), \
             patch("ui.ui_window.connect_to_carla", side_effect=fake_connect), \
             patch("ui.ui_window.setup_environment", lambda w: None), \
             patch("ui.ui_window.cleanup_actors", lambda w: None), \
             patch("ui.ui_window.define_landmarks", lambda w: landmarks), \
             patch("ui.ui_window.GlobalRoutePlanner", FakeGRP):

            dlg = VoiceInputDialog()
            dlg.start_landmark = "school"  # 不在 landmarks
            dlg.end_landmark   = "home"

            # 捕获 warn 文本（TEST_MODE 下会 print）
            with patch.object(VoiceInputDialog, "warn") as mock_warn:
                dlg.show_route()
                QApplication.processEvents(); time.sleep(0.05)
                self.assertTrue(mock_warn.called, "应提示无效地点")

    def test_route_too_short(self):
        fake_world = SimpleNamespace(get_map=lambda: object())
        def fake_connect(): return object(), fake_world, object()

        loc = SimpleNamespace(x=0, y=0, z=0)
        landmarks = {"school": SimpleNamespace(location=loc),
                     "home":   SimpleNamespace(location=loc)}

        class FakeGRP:
            def __init__(self, *a, **k): pass
            def trace_route(self, a, b):
                wp = SimpleNamespace(transform=SimpleNamespace(location=loc))
                return [(wp, "opt")]  # 只有一个点，视为失败

        with patch("ui.ui_window.TEST_MODE", True), \
             patch("ui.ui_window.QPixmap", side_effect=self._fake_pixmap), \
             patch.object(VoiceInputDialog, "update_map", lambda _s: None), \
             patch("ui.ui_window.connect_to_carla", side_effect=fake_connect), \
             patch("ui.ui_window.setup_environment", lambda w: None), \
             patch("ui.ui_window.cleanup_actors", lambda w: None), \
             patch("ui.ui_window.define_landmarks", lambda w: landmarks), \
             patch("ui.ui_window.GlobalRoutePlanner", FakeGRP), \
             patch.object(VoiceInputDialog, "warn") as mock_warn:

            dlg = VoiceInputDialog()
            dlg.start_landmark = "school"
            dlg.end_landmark   = "home"
            dlg.show_route()
            QApplication.processEvents(); time.sleep(0.05)
            self.assertTrue(mock_warn.called, "路径点少于2应提示失败")

if __name__ == "__main__":
    unittest.main(verbosity=2, exit=False)
