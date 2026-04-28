from __future__ import annotations

import contextvars
import enum
import functools
import inspect
import struct
import typing

if typing.TYPE_CHECKING:
  _P = typing.ParamSpec("_P")
  _R = typing.TypeVar("_R")
  _Packer = typing.Callable[..., bytes]
  _Unpacker = typing.Callable[[typing.Any], tuple[typing.Any, ...]]

_STRUCT_ENDIAN = "<"
_MISSING_PAYLOAD = object()
_packed_payload_var = contextvars.ContextVar("pynomata_packed_payload", default=_MISSING_PAYLOAD)

def _payload_bytes(payload):
  if payload is None:
    return b""
  if isinstance(payload, bytes):
    return payload
  if isinstance(payload, (bytearray, memoryview)):
    return bytes(payload)
  if hasattr(payload, "to_bytes"):
    return payload.to_bytes()
  return bytes(payload)

def _unpack_from(fmt, payload, offset):
  fmt = _STRUCT_ENDIAN + fmt
  size = struct.calcsize(fmt)
  if offset + size > len(payload):
    raise ValueError(f"not enough payload bytes for {fmt!r}: need {size}, have {len(payload) - offset}")
  return struct.unpack_from(fmt, payload, offset), offset + size

def _decode_fixed_bytes(raw, encoding):
  raw = raw.split(b"\0", 1)[0]
  return raw.decode(encoding)

def primitive(fmt, cast=None):
  def enc(x):
    if cast is not None:
      x = cast(x)
    return (fmt, (x,))

  def dec(payload, offset):
    (value,), offset = _unpack_from(fmt, payload, offset)
    if cast is not None:
      value = cast(value)
    return value, offset

  enc.__pack_encoder__ = True
  enc.__pack_decoder__ = dec
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

  def dec(payload, offset):
    (raw,), offset = _unpack_from(f"{size}s", payload, offset)
    return _decode_fixed_bytes(raw, encoding), offset

  enc.__pack_encoder__ = True
  enc.__pack_decoder__ = dec
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

  def dec(payload, offset):
    (count, buf), offset = _unpack_from(f"I{max_count * elem_size}s", payload, offset)
    if count > max_count:
      raise ValueError(f"fixed string array count {count} exceeds max_count {max_count}")
    values = []
    for i in range(count):
      start = i * elem_size
      values.append(_decode_fixed_bytes(buf[start:start + elem_size], encoding))
    return values, offset

  enc.__pack_encoder__ = True
  enc.__pack_decoder__ = dec
  return enc

def byte_array(value):
  value = bytes(value)
  return (f"I{len(value)}s", (len(value), value))
byte_array.__pack_encoder__ = True

def _decode_byte_array(payload, offset):
  (size,), offset = _unpack_from("I", payload, offset)
  end = offset + size
  if end > len(payload):
    raise ValueError(f"byte array length {size} exceeds remaining payload {len(payload) - offset}")
  return bytes(payload[offset:end]), end

byte_array.__pack_decoder__ = _decode_byte_array

def enum_value(enum_cls):
  value_enc = encoder_for(getattr(enum_cls, "__pack_type__", u32))
  value_dec = decoder_for(getattr(enum_cls, "__pack_type__", u32))

  def enc(value):
    return value_enc(int(enum_cls(value)))

  def dec(payload, offset):
    value, offset = value_dec(payload, offset)
    return enum_cls(value), offset

  enc.__pack_encoder__ = True
  enc.__pack_decoder__ = dec
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

def _annotation_decoder(annotation):
  origin = typing.get_origin(annotation)
  if origin is typing.Annotated:
    args = typing.get_args(annotation)
    for meta in args[1:]:
      try:
        return decoder_for(meta)
      except TypeError:
        pass
    annotation = args[0]

  if annotation is float:
    return decoder_for(f32)
  if annotation is bool:
    return decoder_for(boolean)
  if annotation is bytes:
    return decoder_for(byte_array)
  if annotation is int:
    raise TypeError("int is ambiguous for binary packing; use u8/u16/u32/u64 or i8/i16/i32/i64")
  if inspect.isclass(annotation) and issubclass(annotation, enum.IntEnum):
    return decoder_for(enum_value(annotation))

  return decoder_for(annotation)

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

def struct_field_decoders(*fields):
  fields = tuple(fields)

  def dec(payload, offset):
    values = {}

    for name, field_dec in fields:
      values[name], offset = field_dec(payload, offset)

    return values, offset

  return dec

_struct_encoder_cache = {}
_struct_decoder_cache = {}

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

def struct_decoder(cls):
  if cls in _struct_decoder_cache:
    return _struct_decoder_cache[cls]

  fields = tuple(
    (name, _annotation_decoder(field_type))
    for name, field_type in _struct_fields_for(cls)
  )

  field_dec = struct_field_decoders(*fields)

  def dec(payload, offset):
    values, offset = field_dec(payload, offset)
    obj = cls.__new__(cls)
    for name, value in values.items():
      setattr(obj, name, value)
    return obj, offset

  dec.__name__ = f"{cls.__name__}_decoder"
  _struct_decoder_cache[cls] = dec
  return dec

def slot_struct(value):
  if inspect.isclass(value):
    return struct_encoder(value)
  return struct_encoder(type(value))(value)

def encoder_for(spec):
  if spec is bool:
    return boolean
  if spec is float:
    return f32
  if spec is bytes:
    return byte_array
  if spec is int:
    raise TypeError("int is ambiguous for binary packing; use u8/u16/u32/u64 or i8/i16/i32/i64")
  if inspect.isclass(spec) and issubclass(spec, enum.IntEnum):
    return enum_value(spec)
  if inspect.isclass(spec):
    return struct_encoder(spec)
  if getattr(spec, "__pack_encoder__", False):
    return spec
  if callable(spec):
    return spec
  raise TypeError(f"cannot build pack encoder from {spec!r}")

def decoder_for(spec):
  if spec is bool:
    return boolean.__pack_decoder__
  if spec is float:
    return f32.__pack_decoder__
  if spec is bytes:
    return byte_array.__pack_decoder__
  if spec is int:
    raise TypeError("int is ambiguous for binary packing; use u8/u16/u32/u64 or i8/i16/i32/i64")
  if inspect.isclass(spec) and issubclass(spec, enum.IntEnum):
    return enum_value(spec).__pack_decoder__
  if inspect.isclass(spec):
    return struct_decoder(spec)
  decoder = getattr(spec, "__pack_decoder__", None)
  if decoder is not None:
    return decoder
  raise TypeError(f"cannot build pack decoder from {spec!r}")

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

def make_unpacker(*decoders, consume_all=True):
  decoders = tuple(decoder_for(dec) for dec in decoders)

  def unpack(payload):
    payload = _payload_bytes(payload)
    offset = 0
    values = []
    for dec in decoders:
      value, offset = dec(payload, offset)
      values.append(value)
    if consume_all and offset != len(payload):
      raise ValueError(f"payload has {len(payload) - offset} trailing bytes")
    return tuple(values)

  return unpack

def decode_as(spec, payload, *, consume_all=True):
  unpack = make_unpacker(spec, consume_all=consume_all)
  (value,) = unpack(payload)
  return value

unpack_as = decode_as

def make_versioned_unpacker(*decoders, version: int = 1, consume_all=True):
  unpack = make_unpacker(u32, *decoders, consume_all=consume_all)

  def unpack_versioned(payload):
    got_version, *values = unpack(payload)
    if got_version != version:
      raise ValueError(f"unsupported payload version {got_version}; expected {version}")
    return tuple(values)

  return unpack_versioned

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

def packed_payload() -> bytes:
  payload = _packed_payload_var.get()
  if payload is _MISSING_PAYLOAD:
    raise RuntimeError("packed_payload() is only available inside a with_payload-decorated call")
  return payload

def with_payload(
  *encoders: typing.Any,
  version: int = 1,
) -> typing.Callable[
  [typing.Callable[typing.Concatenate[typing.Any, _P], _R]],
  typing.Callable[typing.Concatenate[typing.Any, _P], _R],
]:
  def decorate(
    method: typing.Callable[typing.Concatenate[typing.Any, _P], _R],
  ) -> typing.Callable[typing.Concatenate[typing.Any, _P], _R]:
    sig = inspect.signature(method)
    params = list(sig.parameters.values())
    if not params:
      raise TypeError("with_payload methods must accept self")

    payload_params = params[1:]
    versioned_packer = None

    def get_packer():
      nonlocal versioned_packer

      if versioned_packer is None:
        base_packer = make_packer(u32, *encoders)

        def pack_versioned(*values):
          return base_packer(version, *values)

        versioned_packer = pack_versioned

      return versioned_packer

    def build_payload(self: typing.Any, *args: _P.args, **kwargs: _P.kwargs) -> bytes:
      bound = sig.bind(self, *args, **kwargs)
      bound.apply_defaults()

      values = []
      for param in payload_params:
        if param.kind == inspect.Parameter.VAR_POSITIONAL:
          values.extend(bound.arguments.get(param.name, ()))
        elif param.kind == inspect.Parameter.VAR_KEYWORD:
          extra_kwargs = bound.arguments.get(param.name, {})
          if extra_kwargs:
            raise TypeError("with_payload cannot pack variadic keyword arguments")
        else:
          values.append(bound.arguments[param.name])

      return get_packer()(*values)

    if inspect.iscoroutinefunction(method):
      @functools.wraps(method)
      async def async_wrapped(self: typing.Any, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        payload = build_payload(self, *args, **kwargs)
        token = _packed_payload_var.set(payload)
        try:
          return await method(self, *args, **kwargs)
        finally:
          _packed_payload_var.reset(token)

      async_wrapped.__signature__ = sig
      return async_wrapped

    @functools.wraps(method)
    def wrapped(self: typing.Any, *args: _P.args, **kwargs: _P.kwargs) -> _R:
      payload = build_payload(self, *args, **kwargs)
      token = _packed_payload_var.set(payload)
      try:
        return method(self, *args, **kwargs)
      finally:
        _packed_payload_var.reset(token)

    wrapped.__signature__ = sig
    return wrapped

  return decorate
