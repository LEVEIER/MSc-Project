# main.py


from ui.ui_window import MainWindow
from PyQt5.QtWidgets import QApplication

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    app = QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.resize(500, 300)
    mainWin.move(
        (app.primaryScreen().size().width() - mainWin.width()) // 2,
        (app.primaryScreen().size().height() - mainWin.height()) // 2
    )
    mainWin.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()


# # === 主函数 ===
# def main():
#     client, world, blueprint_library = connect_to_carla()
#     setup_environment(world)
#     cleanup_actors(world)
#     landmarks = define_landmarks(world)

#     # get_destination_from_user(landmarks)

#     # Step 1：录音
#     print("[INFO] 请说出终点")
#     audio_file = record_voice()
#     if audio_file is None:
#         print("[ERROR] 无法录音，请检查麦克风设备")
#         return

#     # Step 2：语音转文字
#     text = transcribe_audio(audio_file)
#     if not text:
#         print("[ERROR] 语音识别失败")
#         return
#     print(f"[INFO] 用户说：{text}")

#     # Step 3：用 LLM 解析出 start / end

#     location_data = chat_with_deepseek(text)

#     end_raw = location_data.get("end")
#     end = normalize_place_name(end_raw) if end_raw else "home"

#     start_point = get_random_start_point(landmarks)

#     # 确保终点合法
#     if end not in landmarks:
#         print(f"[ERROR] 无效的终点 '{end}'，可选地点包括: {list(landmarks.keys())}")
#         return

#     end_point = landmarks[end]


#     # Step 4：语音反馈
#     reply_text = f"好的，车辆将从 {start_point} 出发，前往 {end_point}。"
#     asyncio.run(speak(reply_text))

#     # Step 5：启动自动驾驶控制

#     run_autonomous_navigation(client, world, blueprint_library, start_point, end_point)


# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     client, world, blueprint_library = connect_to_carla()
#     landmarks = define_landmarks(world)
    
#     mainWin = MainWindow()
#     mainWin.show()
#     sys.exit(app.exec_())


# # === 语音导航文本交互函数 ===
# def get_destination_from_user(landmarks):
#     print("欢迎使用语音导航系统（模拟文本交互）")
#     print("以下是可选目的地：")
#     for i, name in enumerate(landmarks.keys()):
#         print(f"[{i}] {name}")

#     while True:
#         try:
#             index = int(input("请输入目的地编号(按Enter确认):"))
#             names = list(landmarks.keys())
#             if 0 <= index < len(names):
#                 return names[index]
#             else:
#                 print("编号无效，请重新输入。")
#         except ValueError:
#             print("输入无效，请输入整数编号。")

# def main():
#     # 步骤 1：录音
#     audio_file = record_voice()
#     if audio_file is None:
#         print("[ERROR] 无法录音，请检查麦克风设备")
#         return

#     # 步骤 2：语音转文字
#     text = transcribe_audio(audio_file)
#     if not text:
#         print("[ERROR] 语音识别失败")
#         return
#     print(f"[INFO] 用户说：{text}")

#     # 步骤 3：用 LLM 解析出 start / end
#     location_data = chat_with_deepseek(text)

#     start_raw = location_data.get("start")
#     end_raw = location_data.get("end")

#     start = normalize_location_name(start_raw) if start_raw else "home"
#     end = normalize_location_name(end_raw) if end_raw else "hospital"

#     print(f"[INFO] LLM 解析：从 {start} 到 {end}")

#     # 步骤 4：语音反馈用户
#     reply_text = f"好的，车辆将从 {start} 出发，前往 {end}。"
#     asyncio.run(speak(reply_text))

#     # 步骤 5：启动自动驾驶控制
#     run_autonomous_navigation(start, end)

# if __name__ == "__main__":
#     app = QApplication(sys.argv)
    
#     # 这里需要传入 agent 和 world，如果你还没有，可以临时传 None
#     agent, world = connect_to_carla()  # 确保你有一个 connect_to_carla 函数
#     window = VoiceControlApp(agent, world)

#     sys.exit(app.exec_())
#     main()

