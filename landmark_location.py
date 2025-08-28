import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import carla
from utils.connect_to_carla import connect_to_carla


def define_landmarks(world):

    map = world.get_map()
    spawn_points = map.get_spawn_points()

    landmarks = {
        "home": spawn_points[109],
        "cottageArea": spawn_points[72],
        "hospital": spawn_points[235],
        "school": spawn_points[51],
        "market": spawn_points[283],
        "officeParking": spawn_points[219],
        "shoppingMall": spawn_points[27],
        "office": spawn_points[258],
        "parking": spawn_points[21],
        "railway": spawn_points[138],
    }

    for name, transform in landmarks.items():
        loc = transform.location
        world.debug.draw_string(loc + carla.Location(z=2), 
                                name, draw_shadow=False, color=carla.Color(0, 255, 0), life_time=100.0)
        world.debug.draw_arrow(loc, loc + transform.get_forward_vector() * 2, life_time=100.0)

    return landmarks

def visualize_all_spawn_points(world):
    spawn_points = world.get_map().get_spawn_points()
    print(f"Found {len(spawn_points)} spawn points:\n")

    for i, sp in enumerate(spawn_points):
        loc = sp.location
        rot = sp.rotation
        print(f"[{i}] location: x={loc.x:.2f}, y={loc.y:.2f}, z={loc.z:.2f} | rotation: yaw={rot.yaw:.2f}, pitch={rot.pitch:.2f}, roll={rot.roll:.2f}")

        # 在世界中绘制编号文本
        world.debug.draw_string(loc + carla.Location(z=1.5), f"{i}", life_time=100.0, color=carla.Color(0, 255, 0))
        
        # 在世界中绘制朝向箭头
        forward = sp.get_forward_vector()
        world.debug.draw_arrow(loc, loc + forward * 2, thickness=0.1, arrow_size=0.2, life_time=100.0, color=carla.Color(255, 0, 0))


def main():
    client, world, blueprint_library = connect_to_carla()

   
    landmarks = define_landmarks(world)
    print("Landmarks defined:", landmarks)
    
    visualize_all_spawn_points(world)

    # client.close()

if __name__ == "__main__":
    main()