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

ColorSpace.__pack_type__ = u16

class DataType(IntEnum):
  UNKNOWN = 0
  UINT8 = 1
  UINT16 = 2
  UINT32 = 3
  UINT64 = 4
  INT8 = 5
  INT16 = 6
  INT32 = 7
  INT64 = 8
  FLOAT16 = 9
  FLOAT32 = 10
  FLOAT64 = 11
  BOOL = 12

  @classmethod
  def _missing_(cls, value):
    try:
      import numpy as np

      name = np.dtype(value).name
    except Exception:
      name = getattr(value, "name", value)

    if isinstance(name, str):
      member = cls.__members__.get(name.upper())
      if member is not None:
        return member

    return None

DataType.__pack_type__ = u16

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

class ImageMetadata:
  __slots__ = (
    "width",
    "height",
    "channel_count",
    "color_space",
    "data_type",
  )
  width: Annotated[int, u16]
  height: Annotated[int, u16]
  channel_count: Annotated[int, u16]
  color_space: ColorSpace
  data_type: DataType

  def __init__(
    self,
    width,
    height,
    channel_count,
    *,
    color_space=ColorSpace.RGB,
    data_type=DataType.UINT8,
  ):
    self.width = width
    self.height = height
    self.channel_count = channel_count
    self.color_space = color_space
    self.data_type = data_type
