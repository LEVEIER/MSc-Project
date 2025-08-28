import os, sys, unittest, time
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Qt 相关（headless 环境建议设置 QT_QPA_PLATFORM=offscreen）
from PyQt5.QtWidgets import QApplication
from unittest.mock import patch

# 导入你的对话框类（确保 ui/ui_window.py 能被导入）
from ui.ui_window import VoiceInputDialog

app = None

class TestTTSWrapper(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global app
        if QApplication.instance() is None:
            app = QApplication([])

    @patch("ui.ui_window.asyncio.run")
    @patch("ui.ui_window.speak")
    def test_tts_runs_in_thread(self, mock_speak, mock_asyncio_run):
        dlg = VoiceInputDialog()
        dlg.tts("测试播报")  # 内部应起新线程并调用 asyncio.run(speak(...))

        # 给线程一点时间启动
        time.sleep(0.1)

        self.assertTrue(mock_speak.called)
        self.assertTrue(mock_asyncio_run.called)

if __name__ == "__main__":
    unittest.main()

