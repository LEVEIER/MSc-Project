import os, sys, unittest, math
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from types import SimpleNamespace

def fake_wp(x, y, z=0.0):
    return SimpleNamespace(transform=SimpleNamespace(
        location=SimpleNamespace(x=x, y=y, z=z)
    ))

def route_length(waypoints):
    total = 0.0
    for a, b in zip(waypoints, waypoints[1:]):
        la, lb = a.transform.location, b.transform.location
        dx, dy, dz = la.x - lb.x, la.y - lb.y, la.z - lb.z
        total += math.sqrt(dx*dx + dy*dy + dz*dz)
    return total

class TestRoutePoints(unittest.TestCase):
    def test_strip_pairs_and_length(self):
        pairs = [(fake_wp(0,0), "opt"), (fake_wp(3,4), "opt")]
        wps = [wp for wp, _ in pairs]
        self.assertEqual(len(wps), 2)
        self.assertAlmostEqual(route_length(wps), 5.0, places=4)

if __name__ == "__main__":
    unittest.main()

