# connect_to_carla.py
import carla

def connect_to_carla(host='localhost', port=2000, timeout=10.0):
    client = carla.Client(host, port)
    client.set_timeout(timeout)
    world = client.get_world()
    blueprint_library = world.get_blueprint_library()
    return client, world, blueprint_library