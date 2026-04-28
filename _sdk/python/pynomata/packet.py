from __future__ import annotations

import enum
import functools
import inspect
import struct
import typing

if typing.TYPE_CHECKING:
  _P = typing.ParamSpec("_P")
  _R = typing.TypeVar("_R")
  _Packer = typing.Callable[..., bytes]

def primitive(fmt, cast=None):
  def enc(x):
    if cast is not None:
      x = cast(x)
    return (fmt, (x,))
  enc.__pack_encoder__ = True
  return enc

u8 = primitive("B", int)
u16 = primitive("H", int)
u32 = primitive("I", int)
u64 = primitive("Q", int)

i8 = primitive("b", int)
i16 = primitive("h", int)
i32 = primitive("i", int)
i64 = primitive("q", int)

f32 = primitive("f", float)
f64 = primitive("d", float)
boolean = primitive("?", bool)

def _fixed_bytes(value, size, encoding):
  if size < 1:
    raise ValueError("fixed string size must be at least 1")

  if isinstance(value, bytes):
    raw = value
  else:
    raw = str(value).encode(encoding)

  return raw[:size - 1].ljust(size, b"\0")

def fixed_str(size, encoding="utf-8"):
  def enc(s):
    return (f"{size}s", (_fixed_bytes(s, size, encoding),))
  enc.__pack_encoder__ = True
  return enc

def fixed_str_array(max_count, elem_size, encoding="utf-8"):
  if max_count < 0:
    raise ValueError("max_count must be non-negative")
  if elem_size < 1:
    raise ValueError("fixed string element size must be at least 1")

  def enc(arr):
    arr = list(arr)[:max_count]
    buf = b"".join(
        _fixed_bytes(t, elem_size, encoding)
        for t in arr
    ).ljust(max_count * elem_size, b"\0")
    return (f"I{max_count * elem_size}s", (len(arr), buf))
  enc.__pack_encoder__ = True
  return enc

def byte_array(value):
  value = bytes(value)
  return (f"I{len(value)}s", (len(value), value))
byte_array.__pack_encoder__ = True

def enum_value(enum_cls):
  value_enc = encoder_for(getattr(enum_cls, "__pack_type__", u32))

  def enc(value):
    return value_enc(int(enum_cls(value)))

  enc.__pack_encoder__ = True
  return enc

def _field_value(obj, name):
  if isinstance(obj, dict):
    return obj[name]
  return getattr(obj, name)

def _slots(cls):
  slots = getattr(cls, "__slots__", ())
  if isinstance(slots, str):
    slots = (slots,)
  return tuple(s for s in slots if s not in ("__dict__", "__weakref__"))

def _type_hints(obj):
  try:
    return typing.get_type_hints(obj, include_extras=True)
  except TypeError:
    try:
      return typing.get_type_hints(obj)
    except Exception:
      return getattr(obj, "__annotations__", {})
  except Exception:
    return getattr(obj, "__annotations__", {})

def _annotation_encoder(annotation):
  origin = typing.get_origin(annotation)
  if origin is typing.Annotated:
    args = typing.get_args(annotation)
    for meta in args[1:]:
      try:
        return encoder_for(meta)
      except TypeError:
        pass
    annotation = args[0]

  if annotation is float:
    return f32
  if annotation is bool:
    return boolean
  if annotation is bytes:
    return byte_array
  if annotation is int:
    raise TypeError("int is ambiguous for binary packing; use u8/u16/u32/u64 or i8/i16/i32/i64")
  if inspect.isclass(annotation) and issubclass(annotation, enum.IntEnum):
    return enum_value(annotation)

  return encoder_for(annotation)

def _fields_from_pack_fields(cls, fields):
  slots = _slots(cls)
  if isinstance(fields, dict):
    if slots:
      return [(name, fields[name]) for name in slots]
    return list(fields.items())
  return list(fields)

def _fields_from_annotations(cls):
  hints = _type_hints(cls)
  if not hints:
    return None

  slots = _slots(cls)
  names = slots or tuple(hints.keys())
  missing = [name for name in names if name not in hints]
  if missing:
    raise TypeError(f"{cls.__name__} is missing pack annotations for: {', '.join(missing)}")

  return [(name, hints[name]) for name in names]

def _fields_from_init_annotations(cls):
  init = getattr(cls, "__init__", None)
  if init is None:
    return None

  hints = _type_hints(init)
  if not hints:
    return None

  sig = inspect.signature(init)
  param_names = tuple(
    name for name, param in sig.parameters.items()
    if name != "self" and param.kind in (
      inspect.Parameter.POSITIONAL_ONLY,
      inspect.Parameter.POSITIONAL_OR_KEYWORD,
      inspect.Parameter.KEYWORD_ONLY,
    )
  )
  names = _slots(cls) or param_names
  missing = [name for name in names if name not in hints]
  if missing:
    raise TypeError(f"{cls.__name__}.__init__ is missing pack annotations for: {', '.join(missing)}")

  return [(name, hints[name]) for name in names]

def _struct_fields_for(cls):
  if hasattr(cls, "__pack_fields__"):
    return _fields_from_pack_fields(cls, cls.__pack_fields__)

  slots = _slots(cls)
  if hasattr(cls, "__pack_type__"):
    if not slots:
      raise TypeError(f"{cls.__name__} needs __slots__ when using __pack_type__")
    return [(name, cls.__pack_type__) for name in slots]

  fields = _fields_from_annotations(cls)
  if fields is not None:
    return fields

  fields = _fields_from_init_annotations(cls)
  if fields is not None:
    return fields

  raise TypeError(f"{cls.__name__} has no pack schema; add __pack_type__, __pack_fields__, or annotations")

def struct_fields(*fields):
  fields = tuple((name, encoder_for(field_enc)) for name, field_enc in fields)

  def enc(obj):
    fmt = ""
    flat = []

    for name, field_enc in fields:
      f_fmt, f_vals = field_enc(_field_value(obj, name))
      fmt += f_fmt
      flat.extend(f_vals)

    return (fmt, tuple(flat))

  return enc

_struct_encoder_cache = {}

def struct_encoder(cls):
  if cls in _struct_encoder_cache:
    return _struct_encoder_cache[cls]

  fields = tuple(
    (name, _annotation_encoder(field_type))
    for name, field_type in _struct_fields_for(cls)
  )

  enc = struct_fields(*fields)
  enc.__name__ = f"{cls.__name__}_encoder"
  _struct_encoder_cache[cls] = enc
  return enc

def slot_struct(value):
  if inspect.isclass(value):
    return struct_encoder(value)
  return struct_encoder(type(value))(value)

def encoder_for(spec):
  if inspect.isclass(spec) and issubclass(spec, enum.IntEnum):
    return enum_value(spec)
  if inspect.isclass(spec):
    return struct_encoder(spec)
  if getattr(spec, "__pack_encoder__", False):
    return spec
  if callable(spec):
    return spec
  raise TypeError(f"cannot build pack encoder from {spec!r}")

# little endian struct packing
def make_packer(*encoders):
  encoders = tuple(encoder_for(enc) for enc in encoders)

  def pack(*values):
    if len(values) != len(encoders):
      raise ValueError(f"expected {len(encoders)} values, got {len(values)}")

    fmt = "<"
    flat = []
    for enc, val in zip(encoders, values):
      f_fmt, f_vals = enc(val)
      fmt += f_fmt
      flat.extend(f_vals)
    return struct.pack(fmt, *flat)
  return pack

def with_packer(
  *encoders: typing.Any,
  version: int = 1,
) -> typing.Callable[
  [typing.Callable[typing.Concatenate[typing.Any, _Packer, _P], _R]],
  typing.Callable[typing.Concatenate[typing.Any, _P], _R],
]:
  def decorate(
    method: typing.Callable[typing.Concatenate[typing.Any, _Packer, _P], _R],
  ) -> typing.Callable[typing.Concatenate[typing.Any, _P], _R]:
    versioned_packer = None

    @functools.wraps(method)
    def wrapped(self: typing.Any, *args: _P.args, **kwargs: _P.kwargs) -> _R:
      nonlocal versioned_packer

      if versioned_packer is None:
        base_packer = make_packer(u32, *encoders)

        def pack_versioned(*values):
          return base_packer(version, *values)

        versioned_packer = pack_versioned

      return method(self, versioned_packer, *args, **kwargs)

    sig = inspect.signature(method)
    params = list(sig.parameters.values())
    if len(params) >= 2:
      wrapped.__signature__ = sig.replace(parameters=[params[0], *params[2:]])

    return wrapped

  return decorate
