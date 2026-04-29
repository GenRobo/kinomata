from __future__ import annotations

import sys
from enum import IntEnum
from pathlib import Path
from typing import Annotated

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(PACKAGE_ROOT) not in sys.path:
  sys.path.insert(0, str(PACKAGE_ROOT))

from pynomata import packet
from pynomata.common_types import ColorSpace, DataType, ImageType, Pose, Quat, Vec3


class ScenePacket:
  __slots__ = ("pose", "image", "color")

  pose: Pose
  image: ImageType
  color: ColorSpace

  def __init__(self, pose, image, color):
    self.pose = pose
    self.image = image
    self.color = color


class ExplicitPacket:
  __slots__ = ("image", "color")
  __pack_fields__ = (("image", ImageType), ("color", ColorSpace))

  def __init__(self, image, color):
    self.image = image
    self.color = color


class LocalMode(IntEnum):
  OFF = 0
  ON = 1


def _pose():
  return Pose(Vec3(1.15, 450.0, 2000.567), Quat(0.25, 0.1, 0.2, 1.0))


def _assert_vec3(actual, expected):
  assert actual.x == pytest.approx(expected.x)
  assert actual.y == pytest.approx(expected.y)
  assert actual.z == pytest.approx(expected.z)


def _assert_pose(actual, expected):
  _assert_vec3(actual.pos, expected.pos)
  assert actual.rot.x == pytest.approx(expected.rot.x)
  assert actual.rot.y == pytest.approx(expected.rot.y)
  assert actual.rot.z == pytest.approx(expected.rot.z)
  assert actual.rot.w == pytest.approx(expected.rot.w)


def test_decode_bool_payloads():
  assert packet.decode_as(bool, b"\x01") is True
  assert packet.decode_as(bool, b"\x00") is False


def test_decode_bool_rejects_trailing_and_short_payloads():
  with pytest.raises(ValueError, match="trailing bytes"):
    packet.decode_as(bool, b"\x01\x00")

  with pytest.raises(ValueError, match="not enough payload bytes"):
    packet.decode_as(bool, b"")


def test_spawn_object_payload_shape():
  pack = packet.make_versioned_packer(
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

  pose = _pose()
  scale = Vec3(1.0, 500.0, 1.0)
  payload = pack("cube", ["dynamic", "visible"], pose, scale)
  version, name, tags, decoded_pose, decoded_scale = unpack(payload)

  assert len(payload) == 208
  assert version == 1
  assert name == "cube"
  assert tags == ["dynamic", "visible"]
  _assert_pose(decoded_pose, pose)
  _assert_vec3(decoded_scale, scale)


def test_common_types_round_trip_as_top_level_inputs():
  image = ImageType(
    3,
    2,
    4,
    b"abcdefghijklmnopqrstuvwx",
    image_format="P7",
    data_type=DataType.UINT16,
    color_space=ColorSpace.BGRA,
  )
  pose = _pose()

  pack = packet.make_packer(ColorSpace, Vec3, Quat, Pose, ImageType)
  unpack = packet.make_unpacker(ColorSpace, Vec3, Quat, Pose, ImageType)

  color, vec, quat, decoded_pose, decoded_image = unpack(
    pack(ColorSpace.BGR, pose.pos, pose.rot, pose, image)
  )

  assert color is ColorSpace.BGR
  _assert_vec3(vec, pose.pos)
  assert quat.w == pytest.approx(pose.rot.w)
  _assert_pose(decoded_pose, pose)
  assert decoded_image.width == 3
  assert decoded_image.height == 2
  assert decoded_image.image_format == "P7"
  assert decoded_image.data_type is DataType.UINT16
  assert decoded_image.channel_count == 4
  assert decoded_image.color_space is ColorSpace.BGRA
  assert decoded_image.data == b"abcdefghijklmnopqrstuvwx"


def test_image_type_constructor_stores_values_directly():
  data = bytearray(b"abc")
  image = ImageType(
    "3",
    "2",
    "4",
    data,
    image_format=123,
    data_type="uint16",
    color_space="rgb",
  )

  assert image.width == "3"
  assert image.height == "2"
  assert image.image_format == 123
  assert image.data_type == "uint16"
  assert image.channel_count == "4"
  assert image.color_space == "rgb"
  assert image.data is data


def test_nested_common_type_aggregate_round_trips():
  scene = ScenePacket(
    _pose(),
    ImageType(2, 2, 3, b"abcdefghijkl", color_space="rgb"),
    ColorSpace.GRAY,
  )

  pack = packet.make_packer(ScenePacket)
  unpack = packet.make_unpacker(ScenePacket)
  (decoded,) = unpack(pack(scene))

  _assert_pose(decoded.pose, scene.pose)
  assert decoded.image.width == 2
  assert decoded.image.height == 2
  assert decoded.image.color_space is ColorSpace.RGB
  assert decoded.image.data == b"abcdefghijkl"
  assert decoded.color is ColorSpace.GRAY


def test_enum_string_packing_is_generic():
  pack = packet.make_packer(LocalMode)
  unpack = packet.make_unpacker(LocalMode)

  assert unpack(pack("on")) == (LocalMode.ON,)


def test_data_type_accepts_numpy_dtype_like_values():
  np = pytest.importorskip("numpy")
  pack = packet.make_packer(DataType)
  unpack = packet.make_unpacker(DataType)

  assert unpack(pack(np.uint8)) == (DataType.UINT8,)
  assert unpack(pack(np.dtype("float32"))) == (DataType.FLOAT32,)


def test_explicit_pack_fields_aggregate_round_trips():
  explicit = ExplicitPacket(
    ImageType(1, 1, 3, b"rgb", image_format="P6", data_type="uint8"),
    ColorSpace.RGB,
  )

  pack = packet.make_packer(ExplicitPacket)
  unpack = packet.make_unpacker(ExplicitPacket)
  (decoded,) = unpack(pack(explicit))

  assert decoded.image.width == 1
  assert decoded.image.data == b"rgb"
  assert decoded.color is ColorSpace.RGB


def test_packet_payload_injects_local_payload_inside_method_body():
  class Sender:
    @packet.packet_payload
    def send(self, width: Annotated[int, packet.u16], height: Annotated[int, packet.u16]):
      payload = packet.make_payload()
      return packet.make_unpacker(packet.u32, packet.u16, packet.u16)(payload)

  assert Sender().send(320, 240) == (1, 320, 240)


def test_make_payload_marker_requires_packet_payload_decorator():
  with pytest.raises(RuntimeError, match="packet_payload"):
    packet.make_payload()


def test_packet_payload_requires_make_payload_marker():
  with pytest.raises(TypeError, match="make_payload"):
    class Sender:
      @packet.packet_payload
      def send(self, width: Annotated[int, packet.u16]):
        return width


def test_decode_as_reuses_compiled_unpacker():
  packet.decode_as(bool, b"\x01")
  first = packet._decode_cache[(bool, True)]

  packet.decode_as(bool, b"\x00")

  assert packet._decode_cache[(bool, True)] is first


def test_deleted_decorator_context_apis_are_absent():
  assert not hasattr(packet, "with_payload")
  assert not hasattr(packet, "packed_payload")
  assert not hasattr(packet, "with_packer")
