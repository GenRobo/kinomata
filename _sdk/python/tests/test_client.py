from __future__ import annotations

import inspect

from pynomata.client import KinoClient


def test_client_packed_methods_expose_real_inputs_only():
  assert str(inspect.signature(KinoClient.sim_spawn_object)) == "(self, name, tags, pose, scale)"
  assert str(inspect.signature(KinoClient.sim_start_stream)) == (
    "(self, width, height, count, font_scale, font_thickness)"
  )
