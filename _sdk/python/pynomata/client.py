import zenoh

from .common_types import *
from .packet import *

MAX_NAME_LEN = 32
MAX_TAG_LEN = 16
MAX_TAG_COUNT = 8

class KinoClient:
  def __init__(self):
    conf = zenoh.Config()
    conf.insert_json5("transport/shared_memory/enabled", "true")

    print("Opening session...")
    self.session = zenoh.open(conf)
    self.subs = []

  def reset(self):
    for sub in self.subs:
      sub.undeclare()

  def stop(self):
    self.reset()
    print("Closing session...")
    self.session.close()

  # generic Query-Reply helper
  def sim_qr(self, key_expr:str, payload):
    replies = self.session.get(f"sim/{key_expr}", payload=payload)
    for reply in replies:
      if reply.ok is not None:
        return reply.ok.payload
      else:
        return None

  @with_packer(fixed_str(MAX_NAME_LEN), fixed_str_array(MAX_TAG_COUNT, MAX_TAG_LEN),
               Pose, Vec3)
  def sim_spawn_object(self, _pack, name, tags, pose, scale):
    payload = _pack(name, tags, pose, scale)
    return self.sim_qr("spawn/object", payload).to_string()
