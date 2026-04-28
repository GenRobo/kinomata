from enum import IntEnum
from typing import Annotated

from .packet import *

class ColorSpace(IntEnum):
  UNKNOWN = 0
  GRAY = 1
  RGB = 2
  BGR = 3
  RGBA = 4
  BGRA = 5

ColorSpace.__pack_type__ = u32

class Vec3:
  __slots__ = ("x", "y", "z")
  __pack_type__ = f32

  def __init__(self, x, y, z):
    self.x, self.y, self.z = map(float, (x, y, z))

class Quat:
  __slots__ = ("x", "y", "z", "w")
  __pack_type__ = f32

  def __init__(self, x, y, z, w):
    self.x, self.y, self.z, self.w = map(float, (x, y, z, w))

class Pose:
  __slots__ = ("pos", "rot")

  def __init__(self, pos: Vec3, rot: Quat):
    self.pos = pos
    self.rot = rot

class ImageType:
  __slots__ = (
    "width",
    "height",
    "image_format",
    "data_type",
    "channel_count",
    "color_space",
    "data",
  )
  width: Annotated[int, u32]
  height: Annotated[int, u32]
  image_format: Annotated[str, fixed_str(8)]
  data_type: Annotated[str, fixed_str(16)]
  channel_count: Annotated[int, u32]
  color_space: ColorSpace
  data: bytes

  def __init__(
    self,
    width,
    height,
    channel_count,
    data,
    *,
    image_format="P6",
    data_type="uint8",
    color_space=ColorSpace.RGB,
  ):
    self.width = int(width)
    self.height = int(height)
    self.image_format = str(image_format)
    self.data_type = _dtype_name(data_type)
    self.channel_count = int(channel_count)
    self.color_space = _color_space(color_space)
    self.data = bytes(data)

def _color_space(color_space):
  if isinstance(color_space, str):
    return ColorSpace[color_space.upper()]
  return ColorSpace(color_space)

def _dtype_name(data_type):
  try:
    import numpy as np

    return np.dtype(data_type).name
  except Exception:
    name = getattr(data_type, "__name__", data_type)
    return str(name)
