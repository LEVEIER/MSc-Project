import os, sys, time, unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPixmap
from ui.ui_window import VoiceInputDialog

class TestIntegStartNavigation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def test_voice_to_nav_call_ok(self):
        def fake_qpixmap(*a, **k): return QPixmap(10,10)
        with patch("ui.ui_window.TEST_MODE", True), \
             patch("ui.ui_window.QPixmap", side_effect=fake_qpixmap), \
             patch.object(VoiceInputDialog, "update_map", lambda _s: None):

            dlg = VoiceInputDialog()
            dlg.start_landmark = "school"
            dlg.end_landmark   = "home"

            fake_world = SimpleNamespace(get_map=lambda: object())
            def fake_connect(): return object(), fake_world, object()
            loc = SimpleNamespace(x=0,y=0,z=0)
            landmarks = {"school": SimpleNamespace(location=loc),
                         "home": SimpleNamespace(location=loc)}

            class FakeGRP:
                def __init__(self, *a, **k): pass
                def trace_route(self, a, b):
                    wp = SimpleNamespace(transform=SimpleNamespace(location=loc))
                    return [(wp,"opt"),(wp,"opt")]

            called = {"ok": False}
            def fake_run(start_name, end_name):
                called["ok"] = (start_name=="school" and end_name=="home")

            with patch("ui.ui_window.connect_to_carla", side_effect=fake_connect), \
                 patch("ui.ui_window.setup_environment", lambda w: None), \
                 patch("ui.ui_window.cleanup_actors", lambda w: None), \
                 patch("ui.ui_window.define_landmarks", lambda w: landmarks), \
                 patch("ui.ui_window.GlobalRoutePlanner", FakeGRP), \
                 patch("ui.ui_window.run_autonomous_navigation", side_effect=fake_run):

                dlg.start_navigation()
                QApplication.processEvents(); time.sleep(0.05)

                self.assertTrue(called["ok"])
                self.assertGreaterEqual(len(dlg.route), 2)

if __name__ == "__main__":
    unittest.main(verbosity=2, exit=False)
