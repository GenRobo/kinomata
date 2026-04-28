from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load_packet_module():
  packet_path = Path(__file__).resolve().parents[1] / "pynomata" / "packet.py"
  spec = importlib.util.spec_from_file_location("_pynomata_packet_test", packet_path)
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  return module


packet = _load_packet_module()


def test_decode_bool_payloads():
  assert packet.decode_as(bool, b"\x01") is True
  assert packet.decode_as(bool, b"\x00") is False


def test_decode_bool_rejects_trailing_and_short_payloads():
  with pytest.raises(ValueError, match="trailing bytes"):
    packet.decode_as(bool, b"\x01\x00")

  with pytest.raises(ValueError, match="not enough payload bytes"):
    packet.decode_as(bool, b"")


def test_spawn_object_payload_shape():
  class Vec3:
    __slots__ = ("x", "y", "z")
    __pack_type__ = packet.f32

    def __init__(self, x, y, z):
      self.x = x
      self.y = y
      self.z = z

  class Quat:
    __slots__ = ("x", "y", "z", "w")
    __pack_type__ = packet.f32

    def __init__(self, x, y, z, w):
      self.x = x
      self.y = y
      self.z = z
      self.w = w

  class Pose:
    __slots__ = ("pos", "rot")
    __pack_fields__ = (("pos", Vec3), ("rot", Quat))

    def __init__(self, pos, rot):
      self.pos = pos
      self.rot = rot

  pack = packet.make_packer(
    packet.u32,
    packet.fixed_str(32),
    packet.fixed_str_array(8, 16),
    Pose,
    Vec3,
  )
  unpack = packet.make_unpacker(
    packet.u32,
    packet.fixed_str(32),
    packet.fixed_str_array(8, 16),
    Pose,
    Vec3,
  )

  payload = pack(
    1,
    "cube",
    ["dynamic", "visible"],
    Pose(Vec3(1.15, 450.0, 2000.567), Quat(0.25, 0.1, 0.2, 1.0)),
    Vec3(1.0, 500.0, 1.0),
  )
  version, name, tags, pose, scale = unpack(payload)

  assert len(payload) == 208
  assert version == 1
  assert name == "cube"
  assert tags == ["dynamic", "visible"]
  assert pose.rot.w == 1.0
  assert scale.y == 500.0
