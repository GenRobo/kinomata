from pynomata.client import KinoClient
from pynomata.common_types import Pose, Quat, Vec3

client = KinoClient()

result = client.sim_spawn_object(
  name="cube",
  tags=["dynamic", "visible"],
  pose=Pose(
    pos=Vec3(1.15, 450.0, 2000.567),
    rot=Quat(0.25, 0.1, 0.2, 1.0),
  ),
  scale=Vec3(1.0, 500.0, 1.0),
)

print(result)

client.stop()
