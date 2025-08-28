# Project/evaluation/eval_routes.py
import os, sys, time, csv, argparse
from typing import List, Tuple, Dict
import math

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
CARLA_PYTHONAPI = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
if CARLA_PYTHONAPI not in sys.path:
    sys.path.append(CARLA_PYTHONAPI)
    
# 项目依赖
from utils.connect_to_carla import connect_to_carla
from utils.landmark_location import define_landmarks
from agents.navigation.global_route_planner import GlobalRoutePlanner

def path_length_meters(route_wp_list) -> float:
    """route_wp_list: [carla.Waypoint, ...]"""
    dist = 0.0
    for i in range(len(route_wp_list)-1):
        a = route_wp_list[i].transform.location
        b = route_wp_list[i+1].transform.location
        dx,dy,dz = a.x-b.x, a.y-b.y, a.z-b.z
        dist += math.sqrt(dx*dx+dy*dy+dz*dz)
    return dist

def trace_route(map_obj, start_loc, end_loc, resolution=2.0):
    grp = GlobalRoutePlanner(map_obj, resolution)
    route = grp.trace_route(start_loc, end_loc)
    # 转成纯 waypoint 列表
    return [wp for wp,_ in route]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", default="", help="start:end 用逗号分隔多对，如 'school:home,home:market'")
    ap.add_argument("--out_csv", default="evaluation/routes_results.csv")
    ap.add_argument("--out_txt", default="evaluation/routes_summary.txt")
    args = ap.parse_args()

    client, world, _ = connect_to_carla()
    carla_map = world.get_map()
    landmarks = define_landmarks(world)

    # 默认用一些固定对；也可从命令行传 pairs
    pairs = []
    if args.pairs:
        for seg in args.pairs.split(","):
            s,e = seg.split(":")
            pairs.append((s.strip(), e.strip()))
    else:
        pairs = [
            ("school","home"),
            ("home","market"),
            ("office","hospital"),
            ("parking","shoppingMall"),
            ("cottageArea","railway"),
        ]

    rows = []
    for s_name, e_name in pairs:
        if s_name not in landmarks or e_name not in landmarks:
            print(f"[skip] invalid pair {s_name}->{e_name}")
            continue
        start_loc = landmarks[s_name].location
        end_loc   = landmarks[e_name].location

        # “最短路径”（Dijkstra in GRP，本质上按几何长度）
        shortest = trace_route(carla_map, start_loc, end_loc, resolution=2.0)
        L_short = path_length_meters(shortest)

        # “系统路径”——此处先用相同 GRP 输出；如需差异，可在这儿替换为“系统策略”
        # 例如更粗/更细分辨率，或给拥堵/红绿灯区域加权等（自行扩展）
        system = trace_route(carla_map, start_loc, end_loc, resolution=2.0)
        L_sys = path_length_meters(system)

        delta = (L_sys - L_short) / max(L_short, 1e-6) * 100.0
        rows.append([s_name, e_name, round(L_short,2), round(L_sys,2), round(delta,2)])

    os.makedirs(os.path.dirname(args.out_csv), exist_ok=True)
    with open(args.out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["start","end","shortest_m","system_m","delta_percent"])
        w.writerows(rows)

    avg_gap = round(sum(r[4] for r in rows)/len(rows), 2) if rows else None
    with open(args.out_txt, "w", encoding="utf-8") as f:
        f.write("start,end,shortest_m,system_m,delta_percent\n")
        for r in rows:
            f.write(",".join(map(str, r))+"\n")
        f.write(f"\nAverage ΔL(%): {avg_gap}\n")

    print("✓ Saved:", args.out_csv, "and", args.out_txt)

if __name__ == "__main__":
    main()
