import os, sys, time, unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPixmap
from ui.ui_window import VoiceInputDialog

class TestCarlaConnectErrors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def _fake_pixmap(self, *a, **k): return QPixmap(10, 10)

    def test_connect_to_carla_exception(self):
        with patch("ui.ui_window.TEST_MODE", True), \
             patch("ui.ui_window.QPixmap", side_effect=self._fake_pixmap), \
             patch.object(VoiceInputDialog, "update_map", lambda _s: None), \
             patch("ui.ui_window.connect_to_carla", side_effect=RuntimeError("fake connect error")):

            dlg = VoiceInputDialog()
            dlg.start_landmark = "school"
            dlg.end_landmark   = "home"

            with patch.object(VoiceInputDialog, "crit") as mock_crit:
                dlg.start_navigation()
                QApplication.processEvents(); time.sleep(0.05)
                self.assertTrue(mock_crit.called, "连接异常应触发 crit 提示")

    def test_define_landmarks_exception(self):
        fake_world = SimpleNamespace(get_map=lambda: object())
        def fake_connect(): return object(), fake_world, object()

        with patch("ui.ui_window.TEST_MODE", True), \
             patch("ui.ui_window.QPixmap", side_effect=self._fake_pixmap), \
             patch.object(VoiceInputDialog, "update_map", lambda _s: None), \
             patch("ui.ui_window.connect_to_carla", side_effect=fake_connect), \
             patch("ui.ui_window.setup_environment", lambda w: None), \
             patch("ui.ui_window.cleanup_actors", lambda w: None), \
             patch("ui.ui_window.define_landmarks", side_effect=Exception("fake landmarks error")):

            dlg = VoiceInputDialog()
            dlg.start_landmark = "school"
            dlg.end_landmark   = "home"

            with patch.object(VoiceInputDialog, "crit") as mock_crit:
                dlg.start_navigation()
                QApplication.processEvents(); time.sleep(0.05)
                self.assertTrue(mock_crit.called, "landmarks 异常应触发 crit 提示")

if __name__ == "__main__":
    unittest.main(verbosity=2, exit=False)
