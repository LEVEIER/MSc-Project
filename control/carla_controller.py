# carla_controller.py

import carla
import random
import time
import math
import sys
import os


sys.path.append(os.path.dirname(os.path.dirname(__file__)))

carla_path = '/home/estherlevi/carla/PythonAPI'
sys.path.append(os.path.join(carla_path, 'carla'))
sys.path.append(os.path.join(carla_path, 'agents'))

from agents.navigation.behavior_agent import BehaviorAgent
from utils.landmark_location import define_landmarks
from utils.connect_to_carla import connect_to_carla
from PyQt5.QtWidgets import QMessageBox


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

def get_random_start_point(landmarks):
    return random.choice(list(landmarks.values()))

def spawn_random_vehicle(world, blueprint_library):
    spawn_points = world.get_map().get_spawn_points()
    vehicle_bp = random.choice(blueprint_library.filter('vehicle.*'))
    spawn_point = random.choice(spawn_points)
    vehicle = world.try_spawn_actor(vehicle_bp, spawn_point)
    return vehicle

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
                # 示例：检测限速标志并打印出速度限制
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
        print(f"****---Collision detected with {actor_type}, intensity={intensity:.2f}-----******")

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

                msg = QMessageBox()
                msg.setIcon(QMessageBox.Information)
                msg.setWindowTitle("导航完成/Navigation Complete")
                msg.setText("车辆已到达目的地！/Vehicle has reached the destination!")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.exec_()

                break

            moved = current_location.distance(last_location)
            if moved < 0.1:
                stuck_counter += 1
            else:
                stuck_counter = 0

            if stuck_counter >= max_stuck_frames:
                print("!!!!!!!!!!!---------Vehicle seems to be stuck. Ending navigation.----------!!!!!!!!!!!")

                msg = QMessageBox()
                msg.setIcon(QMessageBox.Information)
                msg.setWindowTitle("导航中断/Navigation Interrupted")
                msg.setText("车辆在导航过程中遇到问题！/Vehicle encountered an issue during navigation!")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.exec_()

                break

            if time.time() - start_time > timeout:
                print("**********----Timeout reached. Ending navigation.----------**********")

                msg = QMessageBox()
                msg.setIcon(QMessageBox.Information)
                msg.setWindowTitle("导航超时/Navigation Timeout")
                msg.setText("车辆在导航过程中超时！/Vehicle timed out during navigation!")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.exec_()

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


def run_autonomous_navigation(start_name: str, end_name: str):

    client, world, blueprint_library = connect_to_carla()
    setup_environment(world)
    cleanup_actors(world)

    landmarks = define_landmarks(world)
    
    if start_name not in landmarks or end_name not in landmarks:
        print(f"[ERROR] Invalid landmark name. Available landmarks: {list(landmarks.keys())}")
        return

    # start_point = landmarks[start_name]
    start_point = landmarks[start_name]
    print(f"[INFO] 用户选择的起点为：{start_point.location}")


    end_point = landmarks[end_name]
    print(f"[INFO] 用户选择的终点为：{end_point.location}")

    map = world.get_map()
    start_waypoint = map.get_waypoint(start_point.location)
    end_waypoint = map.get_waypoint(end_point.location, project_to_road=True, lane_type=carla.LaneType.Driving)

    start_point.rotation = start_waypoint.transform.rotation
    end_location = end_waypoint.transform.location

    if start_point.location.distance(end_location) < 10.0:
        print("Start and end points are too close. Aborting.")
        return

    blueprint_library = world.get_blueprint_library()
    vehicle = setup_vehicle(world, blueprint_library, start_point)
    if not vehicle:
        return

    vehicle.set_autopilot(False)
    set_traffic_lights_time(world)

    sensors = []
    cam = setup_camera(world, vehicle, blueprint_library);      sensors.append(cam)
    radar = setup_radar(world, vehicle, blueprint_library);     sensors.append(radar)
    col = setup_collision_sensor(world, vehicle);               sensors.append(col)


    agent = BehaviorAgent(vehicle, behavior='normal')
    agent.set_destination(end_location)

    route = agent._global_planner.trace_route(vehicle.get_location(), end_location)
    if not route:
        print("[ERROR] Route planning failed. Destination unreachable.")
       
        for s in sensors:
            try: s.stop()
            except: pass
            try: s.destroy()
            except: pass
        try: vehicle.destroy()
        except: pass
        return


    save_route_to_file(route, vehicle, end_location)
    print(f"[INFO] Route from {start_name} to {end_name} planned. Starting navigation.")
    # run_navigation(agent, vehicle, end_location, timeout=300)
    # world.tick()
    try:
        run_navigation(agent, vehicle, end_location, timeout=300)
        world.tick()
    finally:
        for s in sensors:
           
            try: s.stop()
            except: pass
            try: s.destroy()
            except: pass
        try: vehicle.destroy()
        except: pass
        print("Navigation completed and resources cleaned up.")

