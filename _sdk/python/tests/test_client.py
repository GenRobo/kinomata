from __future__ import annotations

import inspect
import sys
import types
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(PACKAGE_ROOT) not in sys.path:
  sys.path.insert(0, str(PACKAGE_ROOT))

sys.modules.setdefault(
  "zenoh",
  types.SimpleNamespace(Config=object, open=lambda conf: None),
)

from pynomata import packet
from pynomata.common_types import Pose, Quat, Vec3
from pynomata import client
from pynomata.client import KinoClient


def _pose():
  return Pose(Vec3(1.15, 450.0, 2000.567), Quat(0.25, 0.1, 0.2, 1.0))


def test_client_methods_expose_required_inputs_only():
  assert str(inspect.signature(KinoClient.sim_spawn_object)) == "(self, name, tags, pose, scale)"
  assert str(inspect.signature(KinoClient.sim_start_stream)) == (
    "(self, width, height, count, font_scale, font_thickness)"
  )
  assert str(inspect.signature(KinoClient.sim_end_stream)) == "(self)"


def test_sim_spawn_object_body_uses_injected_payload(monkeypatch):
  calls = []

  def sim_qr(self, key_expr, payload=None, response_type=None):
    calls.append((key_expr, payload, response_type))
    return True

  monkeypatch.setattr(KinoClient, "sim_qr", sim_qr)
  kino = KinoClient.__new__(KinoClient)
  pose = _pose()
  scale = Vec3(1.0, 500.0, 1.0)

  assert kino.sim_spawn_object("cube", ["dynamic", "visible"], pose, scale) is True

  key_expr, payload, response_type = calls[0]
  assert key_expr == "spawn/object"
  assert response_type is bool

  unpack = packet.make_unpacker(
    packet.u32,
    packet.fixed_str(client.MAX_NAME_LEN),
    packet.fixed_str_array(client.MAX_TAG_COUNT, client.MAX_TAG_LEN),
    Pose,
    Vec3,
  )
  version, name, tags, decoded_pose, decoded_scale = unpack(payload)

  assert version == 1
  assert name == "cube"
  assert tags == ["dynamic", "visible"]
  assert decoded_pose.rot.w == 1.0
  assert decoded_scale.y == 500.0


def test_sim_start_stream_body_uses_injected_payload(monkeypatch):
  calls = []

  def sim_qr(self, key_expr, payload=None, response_type=None):
    calls.append((key_expr, payload, response_type))
    return True

  monkeypatch.setattr(KinoClient, "sim_qr", sim_qr)
  kino = KinoClient.__new__(KinoClient)

  assert kino.sim_start_stream(640, 480, 3, 1.5, 2) is True

  key_expr, payload, response_type = calls[0]
  assert key_expr == "stream"
  assert response_type is bool
  assert packet.make_unpacker(packet.u32, packet.u16, packet.u16, packet.u16, packet.f32, packet.u16)(
    payload
  ) == (1, 640, 480, 3, 1.5, 2)


def test_bool_response_decoding_uses_precompiled_unpacker(monkeypatch):
  def fail_decode_as(*args, **kwargs):
    raise AssertionError("decode_as should not be used for bool responses")

  class Session:
    def get(self, key_expr, payload=None):
      return [types.SimpleNamespace(ok=types.SimpleNamespace(payload=b"\x01"))]

  monkeypatch.setattr(client, "decode_as", fail_decode_as)
  kino = KinoClient.__new__(KinoClient)
  kino.session = Session()

  assert kino.sim_qr("stream/end", response_type=bool) is True


def test_client_no_longer_references_old_packet_apis_or_manual_packers():
  source = inspect.getsource(client)

  assert "with_payload" not in source
  assert "packed_payload" not in source
  assert "with_packer" not in source
  assert "contextvars" not in source
  assert "_pack_spawn_object" not in source
  assert "_pack_start_stream" not in source
  assert "payload = make_payload()" in source
  assert "return self.sim_qr(\"spawn/object\", payload, response_type=bool)" in source
  assert "return self.sim_qr(\"stream\", payload, response_type=bool)" in source


def test_generated_methods_do_not_compile_schema_or_read_metadata_at_call_time(monkeypatch):
  calls = []

  def sim_qr(self, key_expr, payload=None, response_type=None):
    calls.append((key_expr, payload, response_type))
    return True

  def fail_metadata_lookup(*args, **kwargs):
    raise AssertionError("metadata lookup should not run during generated method calls")

  monkeypatch.setattr(KinoClient, "sim_qr", sim_qr)
  monkeypatch.setattr(packet, "_compile_op", fail_metadata_lookup)
  monkeypatch.setattr(packet.inspect, "signature", fail_metadata_lookup)
  monkeypatch.setattr(packet.inspect, "getsource", fail_metadata_lookup)
  monkeypatch.setattr(packet.typing, "get_type_hints", fail_metadata_lookup)
  monkeypatch.setattr(client, "make_payload", fail_metadata_lookup)
  kino = KinoClient.__new__(KinoClient)

  assert kino.sim_spawn_object("cube", ["dynamic"], _pose(), Vec3(1.0, 1.0, 1.0)) is True
  assert kino.sim_start_stream(640, 480, 3, 1.5, 2) is True

  assert [call[0] for call in calls] == ["spawn/object", "stream"]
