from typing import Annotated

import zenoh

from .common_types import *
from .packet import *

MAX_NAME_LEN = 32
MAX_TAG_LEN = 16
MAX_TAG_COUNT = 8

_unpack_bool = make_unpacker(bool)

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

  # generic Subscribe helper
  def sub(self, key_expr, handler):
    self.subs.append(self.session.declare_subscriber(key_expr, handler))

  # generic Query-Reply helper
  def request(self, key_expr:str, payload=None, response_type=None):
    replies = self.session.get(key_expr, payload=payload)
    for reply in replies:
      if reply.ok is not None:
        if response_type is None:
          return reply.ok.payload
        if response_type is bool:
          return _unpack_bool(reply.ok.payload)[0]
        return decode_as(response_type, reply.ok.payload)
      else:
        return None

  @packet_payload
  def sim_spawn_object(
    self,
    name: Annotated[str, fixed_str(MAX_NAME_LEN)],
    tags: Annotated[list[str], fixed_str_array(MAX_TAG_COUNT, MAX_TAG_LEN)],
    pose: Pose,
    scale: Vec3,
  ):
    payload = make_payload()
    return self.request("sim/spawn/object", payload, response_type=bool)

  @packet_payload
  def sim_start_stream(
    self,
    width: Annotated[int, u16],
    height: Annotated[int, u16],
    count: Annotated[int, u16],
    font_scale: float,
    font_thickness: Annotated[int, u16],
  ):
    payload = make_payload()
    return self.request("sim/stream", payload, response_type=ImageMetadata)

  def sim_end_stream(self):
    return self.request("sim/stream/end", response_type=bool)
