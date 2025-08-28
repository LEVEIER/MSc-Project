# ui_window.py

import sys
import os
import carla
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (
    QApplication, QPushButton, QLabel, QVBoxLayout, QWidget,
    QLineEdit, QHBoxLayout, QDialog
)
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QTimer

from nlp.speech_recognizer import transcribe_audio
from nlp.instruction_parser import chat_with_deepseek
from control.carla_controller import run_autonomous_navigation, setup_environment, cleanup_actors
from nlp.instruction_parser import alias_map, normalize_place_name
from utils.connect_to_carla import connect_to_carla
from utils.landmark_location import define_landmarks

from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen, QImage
from PIL import Image
from PyQt5.QtCore import Qt
from agents.navigation.global_route_planner import GlobalRoutePlanner

from nlp.instruction_parser import normalize_place_name,chat_with_deepseek,speak
from nlp.speech_recognizer import record_voice
import threading

import asyncio
import threading

TEST_MODE = globals().get("TEST_MODE", False)
MAP_ORIGIN = (-270, 210)  
SCALE = 2.2


def world_to_pixel(location, origin, scale):
    x = int((location.x - origin[0]) * scale)
    y = int((origin[1] - location.y) * scale)
    # y = int((location.y - origin[1]) * scale)
    return x, y


class VoiceInputDialog(QDialog):
    
    def warn(self, title, text):
        from PyQt5.QtWidgets import QMessageBox
        if TEST_MODE:
            print(f"[WARN] {title}: {text}")
            return
        QMessageBox.warning(self, title, text)

    def crit(self, title, text):
        from PyQt5.QtWidgets import QMessageBox
        if TEST_MODE:
            print(f"[CRIT] {title}: {text}")
            return
        QMessageBox.critical(self, title, text)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.resize(1200, 900)
        self.center()
        self.setWindowTitle("语音输入与导航/Voice Input & Navigation")
        self.start_landmark = None
        self.end_landmark = None
        self.route = []
        self.landmarks = {} 

        self.map_label = QLabel()
        self.pixmap = QPixmap("Town05.png").scaled(1024, 1024, Qt.KeepAspectRatio)
        self.map_label.setPixmap(self.pixmap)
        self.map_label.setFixedSize(self.pixmap.size())


        # self.label = QLabel("请说出导航指令.../Please speak your navigation command...")
        # self.label.setStyleSheet("font-size: 24px;")
        self.info_label = QLabel("请点击“录音”并说出导航指令。/Please click 'Record' and speak your navigation command.")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("font-size: 24px;")

        # layout = QVBoxLayout()
        # layout.addWidget(self.label)
        # self.setLayout(layout)
        # QTimer.singleShot(500, self.process_voice)
        self.record_button = QPushButton("录音/Record")
        self.show_route_button = QPushButton("显示路线/Show Route")
        self.start_nav_button = QPushButton("开始导航/Start Navigation")

        self.show_route_button.setEnabled(False)
        self.start_nav_button.setEnabled(False)

    
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.record_button)
        btn_layout.addWidget(self.show_route_button)
        btn_layout.addWidget(self.start_nav_button)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.map_label)
        main_layout.addWidget(self.info_label)
        main_layout.addLayout(btn_layout)
        self.setLayout(main_layout)

        self.record_button.clicked.connect(self.on_record)
        self.show_route_button.clicked.connect(self.show_route)
        self.start_nav_button.clicked.connect(self.start_navigation)

    def on_record(self):
        self.start_landmark = None
        self.end_landmark = None
        self.route = []

        self.map_label.setPixmap(self.pixmap)

        import os
        if os.path.exists("input.wav"):
            os.remove("input.wav")

        self.info_label.setText("录音中，请说出起点和终点.../Recording, please state the start and end points...")
        self.record_button.setEnabled(False)
        self.show_route_button.setEnabled(False)
        self.start_nav_button.setEnabled(False)

        try:
   
            audio_text = transcribe_audio()
            self.info_label.setText("识别中... / Recognizing...")

            parsed_result = chat_with_deepseek(audio_text)
            start = parsed_result.get("start")
            end = parsed_result.get("end")

            if not start or not end:
                self.info_label.setText("未能识别有效的起点或终点。\nPlease speak clearly the start and end places.")
                return

            self.start_landmark = start
            self.end_landmark = end

            self.info_label.setText(f"识别成功 / Recognition Successful:\n从 {start} 到 {end}")

            self.tts(f"已识别到/Starting recognition: {start} -> {end}。需要我显示路线吗？/ Do you need me to show the route?")

            self.show_route_button.setEnabled(True)

            self.start_nav_button.setEnabled(True)

        except Exception as e:
            self.info_label.setText(f"识别失败: {str(e)}")

        finally:
            self.record_button.setEnabled(True)
    
    def tts(self, text: str, voice: str = "zh-CN-XiaoxiaoNeural"):
        if TEST_MODE:
            print(f"[TTS] {text}")
            return
        def _run():
            try:
                asyncio.run(speak(text, voice=voice))
            except Exception as e:
                print(f"[TTS ERROR] {e}")
        threading.Thread(target=_run, daemon=True).start()


    # def tts(self, text: str, voice: str = "zh-CN-XiaoxiaoNeural"):
    #     """在后台线程里播报 TTS,避免阻塞 UI。"""
    #     def _run():
    #         try:
    #             asyncio.run(speak(text, voice=voice))
    #         except Exception as e:
    #             # 静默失败或打印日志都可
    #             print(f"[TTS ERROR] {e}")
    #     threading.Thread(target=_run, daemon=True).start()

    def center(self):
        screen = QApplication.primaryScreen().availableGeometry()
        size = self.geometry()
        self.move(
            (screen.width() - size.width()) // 2,
            (screen.height() - size.height()) // 2
        )

    def load_map(self):
        
        # 打开 PIL 图像并转为 QPixmap
        pil_img = Image.open("Town05.png").resize((1024, 1024))
        self.original_map = pil_img
        # self.map_pixmap = pil2pixmap(pil_img)
        self.update_map()

    def update_map(self):
        qimg = QPixmap("Town05.png").scaled(1024, 1024)
        # qimg = self.map_pixmap.copy()
        # image_height = qimg.height()

        painter = QPainter()
        painter.begin(qimg)

        # 画 landmarks
        if self.landmarks:
            pen = QPen(QColor("red"))
            pen.setWidth(8)
            painter.setPen(pen)
            for name, transform in self.landmarks.items():
                # x, y = world_to_pixel(transform.location, MAP_ORIGIN, SCALE, image_height)
                x, y = world_to_pixel(transform.location, MAP_ORIGIN, SCALE)
                painter.drawPoint(x, y)
                painter.drawText(x + 5, y - 5, name)
                print(f"Landmark {name}: ({x}, {y})")

        # 画路线
        if self.route:
            print(f"绘制路线，点数: {len(self.route)}")
            pen = QPen(QColor("blue"))
            pen.setWidth(3)
            painter.setPen(pen)
            
            for i in range(len(self.route) - 1):
                x1, y1 = world_to_pixel(self.route[i].transform.location, MAP_ORIGIN, SCALE)
                x2, y2 = world_to_pixel(self.route[i+1].transform.location, MAP_ORIGIN, SCALE)
                painter.drawLine(x1, y1, x2, y2)

        painter.end()
        self.map_label.setPixmap(qimg)
        self.map_label.repaint()

    def show_route(self):
    # 检查语音识别是否完成
        if not self.start_landmark or not self.end_landmark:
            self.info_label.setText("未识别到起点或终点，无法显示路线！/ Not able to show route without start or end landmarks.")
            return

        try:
            client, world, blueprint_library = connect_to_carla()
            setup_environment(world)
            cleanup_actors(world)

            # 获取地标信息
            self.landmarks = define_landmarks(world)
            landmarks = self.landmarks

            # 使用语音识别结果
            start = normalize_place_name(self.start_landmark)
            end = normalize_place_name(self.end_landmark)

            if start not in landmarks or end not in landmarks:
                valid_names = ", ".join(landmarks.keys())
                self.warn("无效地点/Invalid", f"起点或终点不在支持范围内/Not in supported range.\n可选地点有:\n{valid_names}")
                return

            start_point = landmarks[start]
            end_point = landmarks[end]

            # 路径规划
            carla_map = world.get_map()
            grp = GlobalRoutePlanner(carla_map, 2.0)
            route = grp.trace_route(start_point.location, end_point.location)

            if not route or len(route) < 2:
                self.warn("路径规划失败", "未能找到起点和终点之间的可行路线。/ Failed to find a valid route between start and end points.")
                return

            # 提取路径点并更新地图
            self.route = [wp for wp, _ in route]
            self.update_map()
            self.info_label.setText(f"路线已显示 / Route shown: {start} -> {end}")

        except Exception as e:
            self.info_label.setText(f"显示路线失败 / Failed to show route: {e}")
            self.tts("抱歉，起点或终点不在支持范围内，请重试/sorry, please try again。")

    def start_navigation(self):
        if not self.start_landmark or not self.end_landmark:
            self.warn("输入错误/Input Error", "起点和终点不能为空/Start and end cannot be empty.")
            return

        start_name = normalize_place_name(self.start_landmark)
        end_name   = normalize_place_name(self.end_landmark)

        if not start_name or not end_name:
            self.info_label.setText("未能识别有效的起点或终点 / Invalid start or end.")
            return

        try:
            # 连接 CARLA 并准备环境
            client, world, _ = connect_to_carla()
            setup_environment(world)
            cleanup_actors(world)

            # 地标
            self.landmarks = define_landmarks(world)
            landmarks = self.landmarks

            # 校验
            if start_name not in landmarks or end_name not in landmarks:
                valid_names = ", ".join(landmarks.keys())
                self.warn("无效地点/Invalid",
                                    f"起点或终点不在支持范围内/Not in supported range.\n可选地点有:\n{valid_names}")
                self.tts("抱歉，起点或终点不在支持范围内，请重试。")
                return

            start_point = landmarks[start_name]
            end_point   = landmarks[end_name]

            # ✅ 先规划路线，并把 (wp, option) 转成纯 waypoint 列表，供 update_map() 画线
            carla_map = world.get_map()
            grp = GlobalRoutePlanner(carla_map, 2.0)
            full_route = grp.trace_route(start_point.location, end_point.location)
            if not full_route or len(full_route) < 2:
                self.warn("路径规划失败", "未能找到起点和终点之间的可行路线。/ Failed to find a valid route.")
                return

            self.route = [wp for wp, _ in full_route]  # ✅ 关键赋值
            self.update_map()                           # 可视化

            # 语音播报 & 启动自动驾驶（你的 run_autonomous_navigation 接受字符串）
            self.info_label.setText(f"导航/Navigation: {start_name} -> {end_name}")
            self.tts(f"开始导航/Starting navigation: {start_name} -> {end_name}。祝您一路顺风。/ Wish you a smooth journey.")
            run_autonomous_navigation(start_name, end_name)

        except Exception as e:
            self.crit("导航错误", f"导航过程出现异常：{e}")
    def on_navigate_clicked(self):
        self.start_navigation()


    # def start_navigation(self):
    #     if not self.start_landmark or not self.end_landmark:
    #         QMessageBox.warning(self, "输入错误/Input Error", "起点和终点不能为空/Start and end cannot be empty.")
    #         return
        
    #     user_start = normalize_place_name(self.start_landmark)
    #     user_end = normalize_place_name(self.end_landmark)

    #     if user_start and user_end:
    #         self.info_label.setText(f"导航/Navigation: {user_start} -> {user_end}")
    #         self.tts(f"开始导航/Starting navigation: {user_start} -> {user_end}。祝您一路顺风。/ Wish you a smooth journey.")
    #         run_autonomous_navigation(user_start, user_end)
    #     else:
    #         self.info_label.setText("请输入完整的起点和终点/Please enter complete start and end points.")

    # def on_navigate_clicked(self):
        
    #     user_start = normalize_place_name(self.start_landmark)
    #     user_end = normalize_place_name(self.end_landmark)

    #     if not user_start or not user_end:
    #         QMessageBox.warning(self, "输入错误/Input Error", "起点和终点不能为空/Start and end cannot be empty.")
    #         return
        

    #     # 加载 CARLA 环境（避免主程序一开始就加载 CARLA）
    #     client, world, blueprint_library = connect_to_carla()
    #     setup_environment(world)
    #     cleanup_actors(world)
    #     landmarks = define_landmarks(world)
    #     self.landmarks = landmarks  


    #     # 先预计算路线以显示
    #     map = world.get_map()
    #     grp = GlobalRoutePlanner(map, 2.0)
    #     self.route = grp.trace_route(user_start.location, user_end.location)

    #     self.update_map()  

    #     run_autonomous_navigation(user_start, user_end)
    #     self.status_label.setText(f"导航成功/Navigation Successful:{user_start} -> {user_end}")
    #     self.tts(f"已开始导航/Starting navigation: {user_start} -> {user_end}。祝您一路顺风。/ Wish you a smooth journey。")

    

class TextInputWidget(QWidget):
    def __init__(self):
        super().__init__()
     
        self.landmarks = {}   # 初始化地标字典
        self.route = []       # 初始化路线列表
        self.map_label = QLabel()  # 创建地图显示控件
        self.qimg = QPixmap("./Town05.png")  # 替换成你的地图图片路径

        self.initUI()
        self.load_map()


    def initUI(self):
        self.resize(500, 300)
        self.center()

        self.setWindowTitle("文本输入导航/Text Input Navigation")

        self.start_input = QLineEdit()
        self.end_input = QLineEdit()

        self.label = QLabel("请输入起点和终点/Please enter start and end points:")
        self.label.setStyleSheet("font-size: 24px;")

       #        
        self.status_label = QLabel("")  # 用于显示导航状态
        self.status_label.setStyleSheet("font-size: 16px; color: green;")

        self.show_route_button = QPushButton("显示路线/Show Route")
        self.show_route_button.setStyleSheet("font-size: 18px; padding: 10px 20px;")
        self.show_route_button.clicked.connect(self.show_route)
    
        self.button = QPushButton("开始导航/Start Navigation")
        self.button.setStyleSheet("font-size: 18px; padding: 10px 20px;")
        self.button.clicked.connect(self.start_navigation)
        # self.button.clicked.connect(self.on_navigate_clicked)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(QLabel("起点/Start:"))
        layout.addWidget(self.start_input)

        layout.addWidget(QLabel("终点/End:"))
        layout.addWidget(self.end_input)

        layout.addWidget(self.show_route_button)  
        layout.addWidget(self.button)

        # 
        layout.addWidget(self.status_label)
        # 地图显示区域，加入布局
        layout.addWidget(self.map_label)
        
        self.setLayout(layout)

    def center(self):
        screen = QApplication.primaryScreen().availableGeometry()
        size = self.geometry()
        self.move(
            (screen.width() - size.width()) // 2,
            (screen.height() - size.height()) // 2
        )

    def load_map(self):

        # def pil2pixmap(pil_image):
        # # 将 PIL.Image 转换为 QImage
        #     data = pil_image.convert("RGBA").tobytes("raw", "RGBA")
        #     qimage = QImage(data, pil_image.width, pil_image.height, QImage.Format_RGBA8888)
        #     return QPixmap.fromImage(qimage)
        
        # 打开 PIL 图像并转为 QPixmap
        pil_img = Image.open("Town05.png").resize((1024, 1024))
        self.original_map = pil_img
        # self.map_pixmap = pil2pixmap(pil_img)
        self.update_map()

    def update_map(self):
        qimg = QPixmap("Town05.png").scaled(1024, 1024)
        # qimg = self.map_pixmap.copy()
        # image_height = qimg.height()

        painter = QPainter()
        painter.begin(qimg)

        # 画 landmarks
        if self.landmarks:
            pen = QPen(QColor("red"))
            pen.setWidth(8)
            painter.setPen(pen)
            for name, transform in self.landmarks.items():
                # x, y = world_to_pixel(transform.location, MAP_ORIGIN, SCALE, image_height)
                x, y = world_to_pixel(transform.location, MAP_ORIGIN, SCALE)
                painter.drawPoint(x, y)
                painter.drawText(x + 5, y - 5, name)
                print(f"Landmark {name}: ({x}, {y})")

        # 画路线
        if self.route:
            print(f"绘制路线，点数: {len(self.route)}")
            pen = QPen(QColor("blue"))
            pen.setWidth(3)
            painter.setPen(pen)
            # for i in range(len(self.route) - 1):  
            #     wp1, _ = self.route[i]
            #     wp2, _ = self.route[i + 1]
            #     x1, y1 = world_to_pixel(wp1.transform.location, MAP_ORIGIN, SCALE, image_height)
            #     x2, y2 = world_to_pixel(wp2.transform.location, MAP_ORIGIN, SCALE, image_height)
            #     painter.drawLine(x1, y1, x2, y2)
            #     print(f"Route {i}: ({x1}, {y1}) -> ({x2}, {y2})")
            
            for i in range(len(self.route) - 1):
                x1, y1 = world_to_pixel(self.route[i].transform.location, MAP_ORIGIN, SCALE)
                x2, y2 = world_to_pixel(self.route[i+1].transform.location, MAP_ORIGIN, SCALE)
                painter.drawLine(x1, y1, x2, y2)

        painter.end()
        self.map_label.setPixmap(qimg)
        self.map_label.repaint()

    def show_route(self):
        start = self.start_input.text().strip()
        end = self.end_input.text().strip()

        if not start or not end:
            QMessageBox.warning(self, "输入错误/Input Error", "起点和终点不能为空/Start and end cannot be empty.")
            return

        client, world, blueprint_library = connect_to_carla()
        setup_environment(world)
        cleanup_actors(world)

        self.landmarks = define_landmarks(world)
        landmarks = self.landmarks

        start = normalize_place_name(start)
        end = normalize_place_name(end)

        if start not in landmarks or end not in landmarks:
            valid_names = ", ".join(landmarks.keys())
            QMessageBox.warning(self, "无效地点/Invalid", f"起点或终点不在支持范围内。\n可选地点有：\n{valid_names}")
            return

        start_point = landmarks[start]
        end_point = landmarks[end]

        map = world.get_map()
        grp = GlobalRoutePlanner(map, 2.0)
        route = grp.trace_route(start_point.location, end_point.location)

        if not route or len(route) < 2:
            QMessageBox.warning(self, "路径规划失败", "未能找到起点和终点之间的可行路线。")
            return

        # 仅提取 waypoints 以用于绘图
        self.route = [wp for wp, _ in route]
        self.update_map()
        self.status_label.setText(f"路线已显示/Route shown: {start} -> {end}")

    def start_navigation(self):
        start = self.start_input.text().strip()
        end = self.end_input.text().strip()
        if start and end:
            self.label.setText(f"导航/Navigation: {start} -> {end}")
            run_autonomous_navigation(start, end)
        else:
            self.label.setText("请输入完整的起点和终点/Please enter complete start and end points.")
    
    def on_navigate_clicked(self):
        user_start = self.start_input.text().strip()
        user_end = self.end_input.text().strip()

        if not user_start or not user_end:
            QMessageBox.warning(self, "输入错误/Input Error", "起点和终点不能为空/Start and end cannot be empty.")
            return
        
        user_start = alias_map.get(user_start, user_start)
        user_end = alias_map.get(user_end, user_end)

        user_start = normalize_place_name(user_start)
        user_end = normalize_place_name(user_end)


        # 加载 CARLA 环境（避免主程序一开始就加载 CARLA）
        client, world, blueprint_library = connect_to_carla()
        setup_environment(world)
        cleanup_actors(world)
        landmarks = define_landmarks(world)
        self.landmarks = landmarks  


        # LLM 解析（确保调用你的 chat_with_deepseek 或 normalize）
        result = chat_with_deepseek(f"从{user_start}去{user_end}")
        start_name = normalize_place_name.get(result.get("start"), result.get("start")).lower()
        end_name = normalize_place_name.get(result.get("end"), result.get("end")).lower()
        # start_name = normalize_place_name(result.get("start")).lower()
        # end_name = normalize_place_name(result.get("end")).lower()

        if start_name not in landmarks or end_name not in landmarks:
            valid_names = list(landmarks.keys())
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("无效地点/Invalid Location")
            msg.setText("起点或终点不在支持范围内/Invalid.\n可选地点如下/Available locations:\n" + ", ".join(valid_names))
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
            return

        start_point = landmarks[start_name]
        end_point = landmarks[end_name]

        # 先预计算路线以显示
        map = world.get_map()
        grp = GlobalRoutePlanner(map, 2.0)
        self.route = grp.trace_route(start_point.location, end_point.location)

        self.update_map()  # 刷新地图

        # 启动自动驾驶
        run_autonomous_navigation(start_point, end_point)
        self.status_label.setText(f"导航成功/Navigation Successful:{start_name} -> {end_name}")
    


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.resize(800, 600)     # 设置窗口大小
        self.center()             

        self.setWindowTitle("语音控制自动驾驶/Voice-Controlled Autonomous Driving")
        self.label = QLabel("请选择输入方式/Please choose input method:")
        self.label.setStyleSheet("font-size: 24px;")

        self.voice_button = QPushButton("语音输入/Voice Input")
        self.voice_button.setStyleSheet("font-size: 18px; padding: 10px 20px;")
        self.text_button = QPushButton("文本输入/Text Input")
        self.text_button.setStyleSheet("font-size: 18px; padding: 10px 20px;")

        self.voice_button.clicked.connect(self.open_voice_dialog)
        self.text_button.clicked.connect(self.open_text_input)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.voice_button)
        layout.addWidget(self.text_button)
        self.setLayout(layout)
    
    def center(self):
        screen = QApplication.primaryScreen().availableGeometry()
        size = self.geometry()
        self.move(
            (screen.width() - size.width()) // 2,
            (screen.height() - size.height()) // 2
        )

    def open_voice_dialog(self):
        dialog = VoiceInputDialog(self)
        dialog.exec_()

    def open_text_input(self):
        self.text_input_widget = TextInputWidget()
        self.text_input_widget.show()

# 启动界面
# if __name__ == "__main__":
#     import sys
#     app = QApplication(sys.argv)
#     mainWin = MainWindow()
#     mainWin.show()
#     sys.exit(app.exec_())

    # def on_record(self):
    #     self.info_label.setText("录音中，请说出起点和终点.../Recording, please state the start and end points...")
    #     self.record_button.setEnabled(False)

    #     try:
    #         audio_text = transcribe_audio()
    #         parsed_result = chat_with_deepseek(audio_text)
    #         start = parsed_result.get("start")
    #         end = parsed_result.get("end")

    #         if not start or not end:
    #             self.info_label.setText("未能识别有效起点或终点")
    #             return

    #         self.start_landmark = start
    #         self.end_landmark = end
    #         self.info_label.setText(f"识别成功：从 {start} 到 {end}")
    #         self.show_route_button.setEnabled(True)
    #         self.start_nav_button.setEnabled(True)

    #     except Exception as e:
    #         self.info_label.setText(f"识别失败: {e}")

# def process_voice(self):
#         try:
#             self.label.setText("识别中.../Recognizing...")
#             QApplication.processEvents()

#             audio_text = transcribe_audio()
#             self.label.setText(f"识别语音/Recognized speech: {audio_text}")
#             self.label.setStyleSheet("font-size: 18px;")

#             parsed_result = chat_with_deepseek(audio_text)
#             start_landmark = parsed_result.get("start", "current")
#             end_landmark = parsed_result.get("end", "home")


#             self.label.setText(f"导航/Navigation: {start_landmark} -> {end_landmark}")
#             self.label.setStyleSheet("color: green; font-size: 18px;")
#             QApplication.processEvents()

#             run_autonomous_navigation(start_landmark, end_landmark)
#             self.label.setText("导航完成/Navigation complete.")
#         except Exception as e:
#             self.label.setText(f"识别失败/Failed to recognize: {e}")
#             self.label.setStyleSheet("color: red; font-size: 18px;")

# from PyQt5.QtWidgets import QApplication, QPushButton, QLabel, QVBoxLayout, QWidget
# from nlp.speech_recognizer import transcribe_audio
# from nlp.instruction_parser import chat_with_deepseek
# from control.carla_controller import run_autonomous_navigation

# def execute_action(parsed_result):
#     start = parsed_result.get("start", "current")
#     end = parsed_result.get("end", "home")
#     run_autonomous_navigation(start, end)
    
# class VoiceControlApp(QWidget):
#     def __init__(self, world, blueprint_library, landmarks):
#         super().__init__()
#         self.world = world
#         self.blueprint_library = blueprint_library
#         self.landmarks = landmarks
#         self.initUI()

#     def initUI(self):
#         self.setWindowTitle('语音控制自动驾驶')
#         self.label = QLabel('点击按钮开始语音识别', self)
#         self.button = QPushButton('🎙️ 开始识别', self)
#         self.button.clicked.connect(self.on_button_click)

#         layout = QVBoxLayout()
#         layout.addWidget(self.label)
#         layout.addWidget(self.button)
#         self.setLayout(layout)
#         self.show()

#     def on_button_click(self):
#         self.label.setText("请说出起点（例如：从医院出发）")
#         try:
#             start_text = transcribe_audio()
#             self.label.setText(f"识别起点：{start_text}")
#             parsed_start = chat_with_deepseek(start_text)
#             self.start = parsed_start.get("start")

#             self.label.setText("请说出终点（例如：去学校）")
#             end_text = transcribe_audio()
#             self.label.setText(f"识别终点：{end_text}")
#             parsed_end = chat_with_deepseek(end_text)
#             self.end = parsed_end.get("end")

#             self.label.setText(f"导航：{self.start} -> {self.end}")
#             run_autonomous_navigation(self.start, self.end)
#         except Exception as e:
#             self.label.setText(f"出错了: {str(e)}")


