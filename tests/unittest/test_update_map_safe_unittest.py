import os, sys, unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPixmap
from ui.ui_window import VoiceInputDialog

class TestUpdateMapSafe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def test_update_map_various_states(self):
        # Fake QPainter：所有方法 no-op
        class FakePainter:
            def begin(self, *a, **k): return True
            def setPen(self, *a, **k): pass
            def drawPoint(self, *a, **k): pass
            def drawText(self, *a, **k): pass
            def drawLine(self, *a, **k): pass
            def end(self): pass

        def fake_qpixmap(*a, **k): return QPixmap(10, 10)

        with patch("ui.ui_window.TEST_MODE", True), \
             patch("ui.ui_window.QPainter", FakePainter), \
             patch("ui.ui_window.QPixmap", side_effect=fake_qpixmap):

            dlg = VoiceInputDialog()

            # 1) 无 landmarks/route
            dlg.landmarks = {}
            dlg.route = []
            dlg.update_map()  # 不应抛异常

            # 2) 只有 landmarks
            loc = SimpleNamespace(x=1, y=2, z=0)
            dlg.landmarks = {"home": SimpleNamespace(location=loc)}
            dlg.route = []
            dlg.update_map()

            # 3) 只有 route（1000 点）
            wp = SimpleNamespace(transform=SimpleNamespace(location=loc))
            dlg.landmarks = {}
            dlg.route = [wp for _ in range(1000)]
            dlg.update_map()

            # 4) 全都有
            dlg.landmarks = {"school": SimpleNamespace(location=loc)}
            dlg.route = [wp for _ in range(50)]
            dlg.update_map()

            self.assertTrue(True, "update_map 在多种状态下未抛异常即可通过")

if __name__ == "__main__":
    unittest.main(verbosity=2, exit=False)
