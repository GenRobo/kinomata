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

  def sub(self, key_expr, handler):
    self.subs.append(self.session.declare_subscriber(key_expr, handler))

  # generic Query-Reply helper
  def sim_qr(self, key_expr:str, payload=None, response_type=None):
    replies = self.session.get(f"sim/{key_expr}", payload=payload)
    for reply in replies:
      if reply.ok is not None:
        if response_type is None:
          return reply.ok.payload
        return decode_as(response_type, reply.ok.payload)
      else:
        return None

  @with_packer(fixed_str(MAX_NAME_LEN), fixed_str_array(MAX_TAG_COUNT, MAX_TAG_LEN), Pose, Vec3)
  def sim_spawn_object(self, _pack, name, tags, pose, scale):
    payload = _pack(name, tags, pose, scale)
    return self.sim_qr("spawn/object", payload, response_type=bool)

  @with_packer(u16, u16, u16, f32, u16)
  def sim_start_stream(self, _pack, width, height, count, font_scale, font_thickness):
    payload = _pack(width, height, count, font_scale, font_thickness)
    return self.sim_qr("stream", payload, response_type=bool)

  def sim_end_stream(self):
    return self.sim_qr("stream/end", response_type=bool)
