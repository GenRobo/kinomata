from .common_types import ColorSpace
import cv2

_COLOR_CONVERSIONS = {
  (ColorSpace.GRAY, ColorSpace.BGR): cv2.COLOR_GRAY2BGR,
  (ColorSpace.GRAY, ColorSpace.RGB): cv2.COLOR_GRAY2RGB,   # alias of GRAY2BGR in OpenCV
  (ColorSpace.GRAY, ColorSpace.RGBA): cv2.COLOR_GRAY2RGBA,
  (ColorSpace.GRAY, ColorSpace.BGRA): cv2.COLOR_GRAY2BGRA,

  (ColorSpace.RGB, ColorSpace.BGR): cv2.COLOR_RGB2BGR,
  (ColorSpace.RGB, ColorSpace.RGBA): cv2.COLOR_RGB2RGBA,
  (ColorSpace.RGB, ColorSpace.GRAY): cv2.COLOR_RGB2GRAY,
  (ColorSpace.RGB, ColorSpace.BGRA): cv2.COLOR_RGB2BGRA,

  (ColorSpace.BGR, ColorSpace.RGB): cv2.COLOR_BGR2RGB,
  (ColorSpace.BGR, ColorSpace.RGBA): cv2.COLOR_BGR2RGBA,
  (ColorSpace.BGR, ColorSpace.GRAY): cv2.COLOR_BGR2GRAY,
  (ColorSpace.BGR, ColorSpace.BGRA): cv2.COLOR_BGR2BGRA,

  (ColorSpace.RGBA, ColorSpace.BGR): cv2.COLOR_RGBA2BGR,
  (ColorSpace.RGBA, ColorSpace.RGB): cv2.COLOR_RGBA2RGB,
  (ColorSpace.RGBA, ColorSpace.GRAY): cv2.COLOR_RGBA2GRAY,
  (ColorSpace.RGBA, ColorSpace.BGRA): cv2.COLOR_RGBA2BGRA,

  (ColorSpace.BGRA, ColorSpace.BGR): cv2.COLOR_BGRA2BGR,
  (ColorSpace.BGRA, ColorSpace.RGB): cv2.COLOR_BGRA2RGB,
  (ColorSpace.BGRA, ColorSpace.GRAY): cv2.COLOR_BGRA2GRAY,
  (ColorSpace.BGRA, ColorSpace.RGBA): cv2.COLOR_BGRA2RGBA,
}

def convert_color(img, src: ColorSpace, dst: ColorSpace):
  if src == dst:
    return img

  try:
    code = _COLOR_CONVERSIONS[(src, dst)]
  except KeyError as e:
    raise ValueError(f"Unsupported conversion: {src} -> {dst}") from e

  return cv2.cvtColor(img, code)
