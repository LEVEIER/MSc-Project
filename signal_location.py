import carla

# def draw_traffic_signs(world):
#     signs = world.get_actors().filter('traffic.*')
#     debug = world.debug

#     for sign in signs:
#         location = sign.get_location()
#         sign_type = sign.type_id
#         color = carla.Color(255, 255, 0)  # 黄色标示

#         # 在地图上绘制文字
#         debug.draw_string(location + carla.Location(z=2), sign_type, color=color, life_time=60.0)
        
#         # 画个小箭头朝正上
#         debug.draw_arrow(location, location + carla.Location(z=1.5), thickness=0.1, arrow_size=0.2, color=color, life_time=60.0)

#     print(f"Total traffic signs found: {len(signs)}")

def draw_opendrive_signals(world):
    carla_map = world.get_map()
    landmarks = carla_map.get_all_landmarks()
    debug = world.debug

    for lm in landmarks:
        loc = lm.transform.location
        debug.draw_string(loc + carla.Location(z=2.0), f"{lm.name}", color=carla.Color(0, 255, 255), life_time=60.0)

    print(f"Total OpenDRIVE landmarks (signals): {len(landmarks)}")


def visualize_all_spawn_points(world):
    spawn_points = world.get_map().get_spawn_points()
    print(f"Found {len(spawn_points)} spawn points:\n")

    for i, sp in enumerate(spawn_points):
        loc = sp.location
        rot = sp.rotation
        print(f"[{i}] location: x={loc.x:.2f}, y={loc.y:.2f}, z={loc.z:.2f} | rotation: yaw={rot.yaw:.2f}, pitch={rot.pitch:.2f}, roll={rot.roll:.2f}")

        world.debug.draw_string(loc + carla.Location(z=1.5), f"{i}", life_time=100.0, color=carla.Color(0, 255, 0))
        
        forward = sp.get_forward_vector()
        world.debug.draw_arrow(loc, loc + forward * 2, thickness=0.1, arrow_size=0.2, life_time=100.0, color=carla.Color(255, 0, 0))


def main():
    client = carla.Client('localhost', 2000)
    client.set_timeout(10.0)
    
    world = client.get_world()
    
    visualize_all_spawn_points(world)
    # draw_traffic_signs(world)
    draw_opendrive_signals(world)

if __name__ == "__main__":
    main()
