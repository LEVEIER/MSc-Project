from tkinter import Tk, Label, Canvas, Button, PhotoImage
from ui_window import MainWindow  
from PIL import Image, ImageTk  
from utils.landmark_location import define_landmarks
import carla

# 创建窗口
window = Tk()
window.title("Town05 地图")

canvas = Canvas(window, width=1024, height=1024)
canvas.pack()

# 加载地图图像
map_image = Image.open("Town05.png")
map_image = map_image.resize((1024, 1024))
tk_image = ImageTk.PhotoImage(map_image)
canvas.create_image(0, 0, anchor="nw", image=tk_image)
canvas.image = tk_image  # 防止被垃圾回收

MAP_ORIGIN = (-300, 400)  # 图像左上角对应的 CARLA 世界坐标 (x, y)
SCALE = 0.6     

client = carla.Client("localhost", 2000)
client.set_timeout(10.0)
world = client.get_world()
landmarks = define_landmarks(world)
""" 
    在 Tkinter Canvas 上绘制 CARLA 地图中的地标点。
    
    参数:
    - canvas: Tkinter Canvas 实例
    - landmarks: dict,格式为 {名称: carla.Transform}
    - origin: tuple,地图左上角在 CARLA 世界中的 (x, y)
    - scale: float, CARLA 世界坐标到图像坐标的缩放因子（pixels per meter）
    """
def draw_landmarks_on_canvas(canvas, landmarks, origin, scale):
   
    def world_to_pixel(location, origin, scale):
        x = int((location.x - origin[0]) * scale)
        y = int((origin[1] - location.y) * scale)
        return x, y

    for name, transform in landmarks.items():
        loc = transform.location
        x, y = world_to_pixel(loc, origin, scale)

        # 绘制圆形标记
        canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill='red')

        # 绘制地标名称
        canvas.create_text(x, y - 10, text=name, fill='black', font=('Arial', 8))
    
    def draw_route_on_map(canvas, route, map_origin, scale):
        for i in range(len(route) - 1):
            x1, y1 = world_to_pixel(route[i].transform.location, map_origin, scale)
            x2, y2 = world_to_pixel(route[i+1].transform.location, map_origin, scale)
            canvas.create_line(x1, y1, x2, y2, fill='blue', width=2)

