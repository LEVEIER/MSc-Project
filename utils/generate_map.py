import carla
import pygame
import os

def generate_town05_map(output_path="Town05.png", resolution=(2048, 2048), pixels_per_meter=10):
    client = carla.Client("localhost", 2000)
    client.set_timeout(10.0)

    # 加载 Town05 地图
    world = client.load_world("Town05")
    carla_map = world.get_map()

    # 创建 pygame 表面来绘图
    pygame.init()
    surface = pygame.Surface(resolution)
    surface.fill((255, 255, 255))  # 白底

    # 渲染导航网格（Navigation Mesh）
    map_image = carla.Map.generate_waypoint_render(surface, carla_map, resolution, pixels_per_meter)

    # 保存为 PNG 图像
    pygame.image.save(surface, output_path)
    print(f"✅ 地图已保存为 {output_path}")

if __name__ == "__main__":
    generate_town05_map()
