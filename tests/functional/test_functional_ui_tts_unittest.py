import os, sys, time, unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPixmap
from ui.ui_window import VoiceInputDialog

class TestFunctionalUITTS(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def test_button_states_and_tts(self):
        def fake_qpixmap(*a, **k): return QPixmap(10,10)
        with patch("ui.ui_window.TEST_MODE", True), \
             patch("ui.ui_window.QPixmap", side_effect=fake_qpixmap), \
             patch.object(VoiceInputDialog, "update_map", lambda _s: None):

            dlg = VoiceInputDialog()

            # 初始：按钮禁用
            self.assertFalse(dlg.show_route_button.isEnabled())
            self.assertFalse(dlg.start_nav_button.isEnabled())

            # 识别成功：mock ASR/LLM
            with patch("nlp.speech_recognizer.transcribe_audio", return_value="go from school to home"), \
                 patch("nlp.instruction_parser.chat_with_deepseek", return_value={"start":"school","end":"home"}), \
                 patch.object(VoiceInputDialog, "tts") as mock_tts:

                dlg.on_record()
                QApplication.processEvents(); time.sleep(0.05)

                # 成功后按钮启用
                self.assertTrue(dlg.show_route_button.isEnabled())
                self.assertTrue(dlg.start_nav_button.isEnabled())
                # TTS 被调用过（识别成功播报）
                self.assertTrue(mock_tts.called)

            # 再次录音应重置
            with patch("nlp.speech_recognizer.transcribe_audio", return_value=""), \
                 patch("nlp.instruction_parser.chat_with_deepseek", return_value={"start":"","end":""}):

                dlg.on_record()
                QApplication.processEvents(); time.sleep(0.05)
                self.assertFalse(dlg.show_route_button.isEnabled())
                self.assertFalse(dlg.start_nav_button.isEnabled())

if __name__ == "__main__":
    unittest.main(verbosity=2, exit=False)
