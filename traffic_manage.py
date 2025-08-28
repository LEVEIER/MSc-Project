import carla
import random
import time
import math
import sys

sys.path.append('/home/estherlevi/carla/PythonAPI/carla')
from agents.navigation.behavior_agent import BehaviorAgent

def cleanup_actors(world):
    for actor in world.get_actors().filter('*vehicle*'):
        actor.destroy()
    for actor in world.get_actors().filter('*sensor*'):
        actor.destroy()
    print("All existing vehicles and sensors have been destroyed.")

def setup_environment(world):
    settings = world.get_settings()
    settings.synchronous_mode = True
    settings.fixed_delta_seconds = 0.05
    world.apply_settings(settings)

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
        "Office": spawn_points[258],
        "parking": spawn_points[21],
        "railway": spawn_points[138],
    }

    #visualize the landmarks with their transforms
    for name, transform in landmarks.items():
        loc = transform.location
        world.debug.draw_string(loc + carla.Location(z=2), name, draw_shadow=False, color=carla.Color(0, 255, 0), life_time=100.0)
        world.debug.draw_arrow(loc, loc + transform.get_forward_vector() * 2, life_time=100.0)

    if len(spawn_points) < 284:  # 最大用了 index 283
        raise ValueError("the number of spawn_points is insufficient,please switch to Town05 or check the map content.")

    return landmarks

def select_landmark_points(landmarks):
    print("\nlandmark list:")
    for i, name in enumerate(landmarks.keys()):
        print(f"[{i}] {name}")
    
    try:
        start_index = int(input("please select start landmark index: "))
        end_index = int(input("please select end landmark index: "))
        names = list(landmarks.keys())

        if start_index == end_index:
            print("start and end landmarks cannot be the same.")
            return None, None

        start_name = names[start_index]
        end_name = names[end_index]
        print(f"start point: {start_name} -> end point: {end_name}")

        return landmarks[start_name], landmarks[end_name]

    except (ValueError, IndexError):
        print("Invalid input, please enter a valid index.")
        return None, None

def set_traffic_lights_time(world, red_time=3.0, yellow_time=1.0, green_time=3.0):
    traffic_lights = world.get_actors().filter('traffic.traffic_light')
    for light in traffic_lights:
        light.set_red_time(red_time)
        light.set_yellow_time(yellow_time)
        light.set_green_time(green_time)
    print(f"All traffic lights set: red={red_time}s, yellow={yellow_time}s, green={green_time}s")

def detect_and_react_to_landmarks(vehicle, landmarks):
    vehicle_loc = vehicle.get_location()
    world = vehicle.get_world()

    for lm in landmarks:
        lm_loc = lm.transform.location
        dist = lm_loc.distance(vehicle_loc)
        if dist < 8.0:
            lm_name = lm.name.lower()
            if "stop" in lm_name:
                print(f"[SIGNAL DETECTED] Stop sign within {dist:.2f}m. Applying brake.")
                vehicle.apply_control(carla.VehicleControl(throttle=0.0, brake=1.0))
                world.tick()
                time.sleep(3)
            elif "speed" in lm_name:
                #检测限速标志并打印出速度限制
                print(f"[SIGNAL DETECTED] Speed sign: {lm.name}, distance {dist:.2f}m")


def setup_vehicle(world, blueprint_library, start_point):
    vehicle_bp = random.choice(blueprint_library.filter('vehicle.tesla.model3'))

    transform = carla.Transform(start_point.location, start_point.rotation)
    try:
        vehicle = world.spawn_actor(vehicle_bp, transform)

        if world.get_settings().synchronous_mode:
            world.tick()
        else:
            time.sleep(0.1)

        loc = vehicle.get_location()
        if loc.x == 0.0 and loc.y == 0.0:
            print("!!!!!!!!!!-Vehicle seems to be at (0, 0), spawn likely failed or not updated-!!!!!!!!!!!")
        else:
            print(f"YYYYYYYYYYYYYY-----Vehicle spawned at: {loc}------YYYYYYYYYYYYYY")

        return vehicle
    except RuntimeError as e:
        print(f"FFFFFFFFFFF-------Failed to spawn vehicle: {e}--------------FFFFFFFFFFF")
        return None

def setup_camera(world, vehicle, blueprint_library):
    camera_bp = blueprint_library.find('sensor.camera.rgb')
    camera_bp.set_attribute('image_size_x', '800')
    camera_bp.set_attribute('image_size_y', '600')
    camera_transform = carla.Transform(carla.Location(x=1.5, z=2.4))
    camera = world.spawn_actor(camera_bp, camera_transform, attach_to=vehicle)

    def process_image(image):
        image.save_to_disk('_out/%06d.png' % image.frame)

    camera.listen(process_image)
    return camera

def setup_radar(world, vehicle, blueprint_library):
    radar_bp = blueprint_library.find('sensor.other.radar')
    radar_bp.set_attribute('horizontal_fov', '45.0')
    radar_bp.set_attribute('vertical_fov', '20.0')
    radar_bp.set_attribute('range', '20000.0')
    radar_transform = carla.Transform(carla.Location(x=1.5, z=2.4))
    radar = world.spawn_actor(radar_bp, radar_transform, attach_to=vehicle)

    def process_radar(data):
        points = []
        for detection in data:
            azi = detection.azimuth
            alt = detection.altitude
            depth = detection.depth
            pos = carla.Vector3D(depth * math.cos(alt) * math.cos(azi), 
                                 depth * math.cos(alt) * math.sin(azi),
                                 depth * math.sin(alt))
            points.append(pos)
        draw_radar(world, vehicle, points)

    radar.listen(process_radar)
    return radar

def draw_radar(world, vehicle, points):
    debug = world.debug
    base_loc = vehicle.get_location()
    base_rot = vehicle.get_transform().rotation
    forward_vec = base_rot.get_forward_vector()
    right_vec = base_rot.get_right_vector()
    up_vec = base_rot.get_up_vector()
    for p in points:
        loc = base_loc + forward_vec*p.x + right_vec*p.y + up_vec*p.z
        debug.draw_point(loc, size=0.05, life_time=0.06, color=carla.Color(255, 0, 0))

def follow_vehicle_spectator(world, vehicle):
    spectator = world.get_spectator()
    transform = vehicle.get_transform()
    location = transform.location + carla.Location(z=40) - transform.get_forward_vector()*10
    rotation = carla.Rotation(pitch=-60, yaw=transform.rotation.yaw)
    spectator.set_transform(carla.Transform(location, rotation))

def setup_traffic_vehicle(client,world, vehicle):

    tm = client.get_trafficmanager(8000)
    tm.set_synchronous_mode(True)
    tm.set_global_distance_to_leading_vehicle(1.0)
    tm.set_hybrid_physics_mode(True)  # 让远处车辆使用轻量级物理模型
    tm.set_respawn_dormant_vehicles(True)
    
    tm.ignore_vehicles_percentage(vehicle, 100.0)  # 忽略当前车辆

    blueprint_library = world.get_blueprint_library()
    vehicle_blueprints = blueprint_library.filter('vehicle.*')
    spawn_points = world.get_map().get_spawn_points()

    vehicles_list = []

    for _ in range(100):  # 生成100辆车
        blueprint = random.choice(vehicle_blueprints)

        if blueprint.has_attribute('speed'):
            blueprint.set_attribute('speed', '80')  # 设置速度上限为80%（可选）
        if blueprint.has_attribute('lane_change'):
            blueprint.set_attribute('lane_change', '1')  # 允许变道
        if blueprint.has_attribute('distance_to_leading_vehicle'):
            blueprint.set_attribute('distance_to_leading_vehicle', '1.0')  # 跟车距离

        spawn_point = random.choice(spawn_points)
        npc_vehicle = world.try_spawn_actor(blueprint, spawn_point)
        if npc_vehicle:
            npc_vehicle.set_autopilot(True, 8000)  # 8000 是 Traffic Manager 的端口
            vehicles_list.append(npc_vehicle)

    world.tick() 
    print("Traffic manager has been set up with synchronous mode and hybrid physics.")
    return tm

def setup_collision_sensor(world, vehicle):
    collision_bp = world.get_blueprint_library().find('sensor.other.collision')
    collision_sensor = world.spawn_actor(collision_bp, carla.Transform(), attach_to=vehicle)

    def on_collision(event):
        actor_type = event.other_actor.type_id
        impulse = event.normal_impulse
        intensity = math.sqrt(impulse.x**2 + impulse.y**2 + impulse.z**2)
        print(f"**************------Collision detected with {actor_type}, intensity={intensity:.2f}--------**************")

    collision_sensor.listen(lambda event: on_collision(event))
    return collision_sensor


def run_navigation(agent, vehicle, end_location, timeout=300):
    world = vehicle.get_world()
    last_location = vehicle.get_location()
    stuck_counter = 0
    max_stuck_frames = 600

    custom_signals = [
    {"name": "Stop", "location": carla.Location(x=123, y=45, z=0.5)},
    {"name": "SpeedLimit30", "location": carla.Location(x=200, y=78, z=0.5)}
]
    triggered_signals = set()

    try:
        start_time = time.time()

        while True:
             
            current_location = vehicle.get_location()
           
            for idx, sign in enumerate(custom_signals):
                dist = sign["location"].distance(current_location)

                if dist < 8.0 and idx not in triggered_signals:
                    if "Stop" in sign["name"]:
                        print(f"==> STOP sign detected at {dist:.2f}m. Braking.")
                        vehicle.apply_control(carla.VehicleControl(throttle=0.0, brake=1.0))
                        world.tick()
                        time.sleep(3)
                        triggered_signals.add(idx)

                    elif "SpeedLimit30" in sign["name"]:
                        print("==> Speed limit 30 detected. Reducing speed.")
                        agent.set_target_speed(30)
                        triggered_signals.add(idx)

            control = agent.run_step()
            vehicle.apply_control(control)
            follow_vehicle_spectator(world, vehicle)

            print(f"Vehicle location: {current_location}, goal: {end_location}")
           
            distance = current_location.distance(end_location)
            print(f"Current distance to goal: {distance:.2f} meters")

            if distance < 5.0:
                print("YYYYYYYYYYYYY---------Vehicle has reached the destination!---------YYYYYYYYYYYYY")
                break

            moved = current_location.distance(last_location)
            if moved < 0.1:
                stuck_counter += 1
            else:
                stuck_counter = 0

            if stuck_counter >= max_stuck_frames:
                print("!!!!!!!!!!!---------Vehicle seems to be stuck. Ending navigation.----------!!!!!!!!!!!")
                break

            if time.time() - start_time > timeout:
                print("**********----Timeout reached. Ending navigation.----------**********")
                break

            last_location = current_location

            world.tick()
            time.sleep(0.1)
    finally:
        vehicle.destroy()
        print("Navigation completed and resources cleaned up.")

def save_route_to_file(route, vehicle, destination, filename="planned_route.txt"):
    current_location = vehicle.get_location()
    remaining_distance = current_location.distance(destination)

    with open(filename, "w") as f:
        f.write(f"Remaining Distance to Goal: {remaining_distance:.2f} meters\n")
        f.write("Waypoint_X,Waypoint_Y,Waypoint_Z, Road_ID, Lane_ID\n")
        for wp, _ in route:
            location = wp.transform.location
            road_id = wp.road_id
            lane_id = wp.lane_id
            f.write(f"{location.x:.2f},{location.y:.2f},{location.z:.2f},{road_id},{lane_id}\n")

def main():
    client = carla.Client('localhost', 2000)
    client.set_timeout(10.0)
    world = client.get_world()

    setup_environment(world)
    cleanup_actors(world)

    landmarks = define_landmarks(world)
    start_point, end_point = select_landmark_points(landmarks)
    if not start_point or not end_point:
        print("landmark selection invalid, program terminated.")
        return

    # 对起点和终点做 map 校正
    map = world.get_map()
    start_waypoint = map.get_waypoint(start_point.location)
    end_waypoint = map.get_waypoint(end_point.location, project_to_road=True, lane_type=carla.LaneType.Driving)

    start_point.rotation = start_waypoint.transform.rotation
    end_location = end_waypoint.transform.location

    print(f"Selected Start Location: {start_point.location}")
    print(f"Selected End Location: {end_location}")

    if start_point.location.distance(end_location) < 10.0:
        print("start and end points are too close, please reselect.")
        return

    blueprint_library = world.get_blueprint_library()
    vehicle = setup_vehicle(world, blueprint_library, start_point)
    if not vehicle:
        return
    vehicle.set_autopilot(False) 
    
    set_traffic_lights_time(world, red_time=3.0, yellow_time=1.0, green_time=3.0)

    setup_camera(world, vehicle, blueprint_library)
    setup_radar(world, vehicle, blueprint_library)
    setup_collision_sensor(world, vehicle)
    setup_traffic_vehicle(client,world, vehicle)

    agent = BehaviorAgent(vehicle, behavior='normal')
    agent.set_destination(end_waypoint.transform.location)

    route = agent._global_planner.trace_route(vehicle.get_location(), end_location)
    if len(route) == 0:
        print("path planning failed, destination unreachable.")
        vehicle.destroy()
        return
    else:
        print(f"There are {len(route)} waypoints found in the planned route.")
        save_route_to_file(route, vehicle, end_location, filename="planned_route.txt")
        print("Route information has been saved to planned_route.txt")

#     custom_signals = [
#         {"name": "Stop", "location": start_point.location + carla.Location(x=8, y=0, z=0)},
#         {"name": "SpeedLimit30", "location": start_point.location + carla.Location(x=15, y=0, z=0)}
# ]
    run_navigation(agent, vehicle, end_location, timeout=300)
    world.tick()

if __name__ == '__main__':
    main()

