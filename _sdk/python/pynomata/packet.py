from __future__ import annotations

import ast
import enum
import inspect
import struct
import textwrap
import typing
from dataclasses import dataclass

_STRUCT_ENDIAN = "<"
_UINT32 = struct.Struct(_STRUCT_ENDIAN + "I")

__all__ = [
  "PrimitiveSpec",
  "FixedStrSpec",
  "FixedStrArraySpec",
  "ByteArraySpec",
  "FixedArraySpec",
  "primitive",
  "fixed_str",
  "fixed_str_array",
  "byte_array",
  "fixed_array",
  "u8",
  "u16",
  "u32",
  "u64",
  "i8",
  "i16",
  "i32",
  "i64",
  "f32",
  "f64",
  "boolean",
  "make_packer",
  "make_versioned_packer",
  "make_unpacker",
  "make_versioned_unpacker",
  "decode_as",
  "unpack_as",
  "make_payload",
  "packet_payload",
]


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


def _decode_fixed_bytes(raw, encoding):
  raw = raw.split(b"\0", 1)[0]
  return raw.decode(encoding)


def _fixed_bytes(value, size, encoding):
  if isinstance(value, bytes):
    raw = value
  else:
    raw = str(value).encode(encoding)
  return raw[:size - 1].ljust(size, b"\0")


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


@dataclass(frozen=True)
class PrimitiveSpec:
  fmt: str
  cast: typing.Callable[[typing.Any], typing.Any] | None = None


@dataclass(frozen=True)
class FixedStrSpec:
  size: int
  encoding: str = "utf-8"


@dataclass(frozen=True)
class FixedStrArraySpec:
  max_count: int
  elem_size: int
  encoding: str = "utf-8"


@dataclass(frozen=True)
class ByteArraySpec:
  pass


@dataclass(frozen=True)
class FixedArraySpec:
  max_count: int
  elem_spec: object


u8 = PrimitiveSpec("B", int)
u16 = PrimitiveSpec("H", int)
u32 = PrimitiveSpec("I", int)
u64 = PrimitiveSpec("Q", int)

i8 = PrimitiveSpec("b", int)
i16 = PrimitiveSpec("h", int)
i32 = PrimitiveSpec("i", int)
i64 = PrimitiveSpec("q", int)

f32 = PrimitiveSpec("f", float)
f64 = PrimitiveSpec("d", float)
boolean = PrimitiveSpec("?", bool)
byte_array = ByteArraySpec()


def primitive(fmt, cast=None):
  return PrimitiveSpec(fmt, cast)


def fixed_str(size, encoding="utf-8"):
  if size < 1:
    raise ValueError("fixed string size must be at least 1")
  return FixedStrSpec(size, encoding)


def fixed_str_array(max_count, elem_size, encoding="utf-8"):
  if max_count < 0:
    raise ValueError("max_count must be non-negative")
  if elem_size < 1:
    raise ValueError("fixed string element size must be at least 1")
  return FixedStrArraySpec(max_count, elem_size, encoding)


def fixed_array(max_count, elem_spec):
  if max_count < 0:
    raise ValueError("max_count must be non-negative")
  return FixedArraySpec(max_count, elem_spec)


class _Op:
  def pack_into(self, chunks, value):
    raise NotImplementedError

  def unpack_from(self, payload, offset):
    raise NotImplementedError


class _PrimitiveOp(_Op):
  __slots__ = ("_cast", "_struct")

  def __init__(self, spec):
    self._struct = struct.Struct(_STRUCT_ENDIAN + spec.fmt)
    self._cast = spec.cast

  def pack_into(self, chunks, value):
    if self._cast is not None:
      value = self._cast(value)
    chunks.append(self._struct.pack(value))

  def unpack_from(self, payload, offset):
    end = offset + self._struct.size
    if end > len(payload):
      raise ValueError(
        f"not enough payload bytes for {self._struct.format!r}: "
        f"need {self._struct.size}, have {len(payload) - offset}"
      )
    (value,) = self._struct.unpack_from(payload, offset)
    if self._cast is not None:
      value = self._cast(value)
    return value, end


class _FixedStrOp(_Op):
  __slots__ = ("_encoding", "_struct")

  def __init__(self, spec):
    self._struct = struct.Struct(_STRUCT_ENDIAN + f"{spec.size}s")
    self._encoding = spec.encoding

  def pack_into(self, chunks, value):
    chunks.append(self._struct.pack(_fixed_bytes(value, self._struct.size, self._encoding)))

  def unpack_from(self, payload, offset):
    end = offset + self._struct.size
    if end > len(payload):
      raise ValueError(
        f"not enough payload bytes for {self._struct.format!r}: "
        f"need {self._struct.size}, have {len(payload) - offset}"
      )
    (raw,) = self._struct.unpack_from(payload, offset)
    return _decode_fixed_bytes(raw, self._encoding), end


class _FixedStrArrayOp(_Op):
  __slots__ = ("_encoding", "_elem_size", "_max_count", "_struct")

  def __init__(self, spec):
    self._max_count = spec.max_count
    self._elem_size = spec.elem_size
    self._encoding = spec.encoding
    self._struct = struct.Struct(_STRUCT_ENDIAN + f"I{spec.max_count * spec.elem_size}s")

  def pack_into(self, chunks, value):
    values = list(value)[:self._max_count]
    buf = b"".join(
      _fixed_bytes(item, self._elem_size, self._encoding)
      for item in values
    ).ljust(self._max_count * self._elem_size, b"\0")
    chunks.append(self._struct.pack(len(values), buf))

  def unpack_from(self, payload, offset):
    end = offset + self._struct.size
    if end > len(payload):
      raise ValueError(
        f"not enough payload bytes for {self._struct.format!r}: "
        f"need {self._struct.size}, have {len(payload) - offset}"
      )
    count, buf = self._struct.unpack_from(payload, offset)
    if count > self._max_count:
      raise ValueError(f"fixed string array count {count} exceeds max_count {self._max_count}")
    values = []
    for i in range(count):
      start = i * self._elem_size
      values.append(_decode_fixed_bytes(buf[start:start + self._elem_size], self._encoding))
    return values, end


class _ByteArrayOp(_Op):
  __slots__ = ()

  def pack_into(self, chunks, value):
    value = bytes(value)
    chunks.append(_UINT32.pack(len(value)))
    chunks.append(value)

  def unpack_from(self, payload, offset):
    end = offset + _UINT32.size
    if end > len(payload):
      raise ValueError(
        f"not enough payload bytes for {_UINT32.format!r}: "
        f"need {_UINT32.size}, have {len(payload) - offset}"
      )
    (size,) = _UINT32.unpack_from(payload, offset)
    data_start = end
    data_end = data_start + size
    if data_end > len(payload):
      raise ValueError(f"byte array length {size} exceeds remaining payload {len(payload) - data_start}")
    return bytes(payload[data_start:data_end]), data_end


class _EnumOp(_Op):
  __slots__ = ("_enum_cls", "_value_op")

  def __init__(self, enum_cls, value_op):
    self._enum_cls = enum_cls
    self._value_op = value_op

  def pack_into(self, chunks, value):
    if isinstance(value, str):
      value = self._enum_cls[value.upper()]
    else:
      value = self._enum_cls(value)
    self._value_op.pack_into(chunks, int(value))

  def unpack_from(self, payload, offset):
    value, offset = self._value_op.unpack_from(payload, offset)
    return self._enum_cls(value), offset


class _StructOp(_Op):
  __slots__ = ("_cls", "_fields")

  def __init__(self, cls, fields):
    self._cls = cls
    self._fields = tuple(fields)

  def pack_into(self, chunks, value):
    for name, op in self._fields:
      op.pack_into(chunks, _field_value(value, name))

  def unpack_from(self, payload, offset):
    obj = self._cls.__new__(self._cls)
    for name, op in self._fields:
      value, offset = op.unpack_from(payload, offset)
      setattr(obj, name, value)
    return obj, offset


class _FixedArrayOp(_Op):
  __slots__ = ("_elem_op", "_elem_size", "_max_count")

  def __init__(self, spec):
    self._max_count = spec.max_count
    self._elem_op = _compile_op(spec.elem_spec)
    self._elem_size = _op_wire_size(self._elem_op)

  def pack_into(self, chunks, value):
    values = list(value)[:self._max_count]
    count = len(values)
    chunks.append(_UINT32.pack(count))
    elem_chunks = []
    for v in values:
      self._elem_op.pack_into(elem_chunks, v)
    packed = b"".join(elem_chunks)
    total_size = self._max_count * self._elem_size
    chunks.append(packed.ljust(total_size, b"\0"))

  def unpack_from(self, payload, offset):
    end = offset + _UINT32.size
    if end > len(payload):
      raise ValueError(
        f"not enough payload bytes for fixed_array count: "
        f"need {_UINT32.size}, have {len(payload) - offset}"
      )
    (count,) = _UINT32.unpack_from(payload, offset)
    offset = end
    if count > self._max_count:
      raise ValueError(f"fixed array count {count} exceeds max_count {self._max_count}")
    total_size = self._max_count * self._elem_size
    if offset + total_size > len(payload):
      raise ValueError(
        f"not enough payload bytes for fixed_array data: "
        f"need {total_size}, have {len(payload) - offset}"
      )
    values = []
    for i in range(count):
      value, offset = self._elem_op.unpack_from(payload, offset)
      values.append(value)
    # skip remaining unused element slots
    offset += (self._max_count - count) * self._elem_size
    return values, offset


def _op_wire_size(op):
  """Return the fixed wire size in bytes, or raise TypeError if variable."""
  if isinstance(op, _PrimitiveOp):
    return op._struct.size
  if isinstance(op, _FixedStrOp):
    return op._struct.size
  if isinstance(op, _FixedStrArrayOp):
    return op._struct.size
  if isinstance(op, _EnumOp):
    return _op_wire_size(op._value_op)
  if isinstance(op, _StructOp):
    return sum(_op_wire_size(field_op) for _, field_op in op._fields)
  if isinstance(op, _FixedArrayOp):
    return _UINT32.size + op._max_count * op._elem_size
  raise TypeError(
    f"cannot determine fixed wire size for {type(op).__name__}; "
    f"fixed_array elements must have a known fixed size"
  )


_op_cache = {}
_packer_cache = {}
_versioned_packer_cache = {}
_unpacker_cache = {}
_versioned_unpacker_cache = {}
_decode_cache = {}


def _annotation_spec(annotation):
  origin = typing.get_origin(annotation)
  if origin is typing.Annotated:
    args = typing.get_args(annotation)
    for meta in args[1:]:
      try:
        _compile_op(meta)
      except TypeError:
        continue
      return meta
    annotation = args[0]

  if annotation is float:
    return f32
  if annotation is bool:
    return boolean
  if annotation is bytes:
    return byte_array
  if annotation is int:
    raise TypeError("int is ambiguous for binary packing; use u8/u16/u32/u64 or i8/i16/i32/i64")
  return annotation


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
  if hasattr(cls, "__pack_type__") and slots:
    return [(name, cls.__pack_type__) for name in slots]

  fields = _fields_from_annotations(cls)
  if fields is not None:
    return fields

  fields = _fields_from_init_annotations(cls)
  if fields is not None:
    return fields

  if hasattr(cls, "__pack_type__"):
    raise TypeError(f"{cls.__name__} needs __slots__ when using __pack_type__")
  raise TypeError(f"{cls.__name__} has no pack schema; add __pack_type__, __pack_fields__, or annotations")


def _compile_op(spec):
  spec = _annotation_spec(spec)
  cached = _op_cache.get(spec)
  if cached is not None:
    return cached

  if isinstance(spec, PrimitiveSpec):
    op = _PrimitiveOp(spec)
  elif isinstance(spec, FixedStrSpec):
    op = _FixedStrOp(spec)
  elif isinstance(spec, FixedStrArraySpec):
    op = _FixedStrArrayOp(spec)
  elif isinstance(spec, ByteArraySpec):
    op = _ByteArrayOp()
  elif isinstance(spec, FixedArraySpec):
    op = _FixedArrayOp(spec)
  elif inspect.isclass(spec) and issubclass(spec, enum.IntEnum):
    op = _EnumOp(spec, _compile_op(getattr(spec, "__pack_type__", u32)))
  elif inspect.isclass(spec):
    fields = tuple((name, _compile_op(field_type)) for name, field_type in _struct_fields_for(spec))
    op = _StructOp(spec, fields)
  else:
    raise TypeError(f"cannot build packet schema from {spec!r}")

  _op_cache[spec] = op
  return op


def _pack_values(ops, values):
  if len(values) != len(ops):
    raise ValueError(f"expected {len(ops)} values, got {len(values)}")

  chunks = []
  for op, value in zip(ops, values):
    op.pack_into(chunks, value)
  return b"".join(chunks)


def _unpack_values(ops, payload, consume_all):
  payload = _payload_bytes(payload)
  offset = 0
  values = []
  for op in ops:
    value, offset = op.unpack_from(payload, offset)
    values.append(value)
  if consume_all and offset != len(payload):
    raise ValueError(f"payload has {len(payload) - offset} trailing bytes")
  return tuple(values)


def make_packer(*specs):
  key = tuple(specs)
  cached = _packer_cache.get(key)
  if cached is not None:
    return cached

  ops = tuple(_compile_op(spec) for spec in specs)

  def pack(*values):
    return _pack_values(ops, values)

  _packer_cache[key] = pack
  return pack


def make_versioned_packer(*specs, version: int = 1):
  key = (version, *specs)
  cached = _versioned_packer_cache.get(key)
  if cached is not None:
    return cached

  version_op = _compile_op(u32)
  value_ops = tuple(_compile_op(spec) for spec in specs)

  def pack(*values):
    if len(values) != len(value_ops):
      raise ValueError(f"expected {len(value_ops)} values, got {len(values)}")

    chunks = []
    version_op.pack_into(chunks, version)
    for op, value in zip(value_ops, values):
      op.pack_into(chunks, value)
    return b"".join(chunks)

  _versioned_packer_cache[key] = pack
  return pack


def make_unpacker(*specs, consume_all=True):
  key = (tuple(specs), consume_all)
  cached = _unpacker_cache.get(key)
  if cached is not None:
    return cached

  ops = tuple(_compile_op(spec) for spec in specs)

  def unpack(payload):
    return _unpack_values(ops, payload, consume_all)

  _unpacker_cache[key] = unpack
  return unpack


def make_versioned_unpacker(*specs, version: int = 1, consume_all=True):
  key = (version, tuple(specs), consume_all)
  cached = _versioned_unpacker_cache.get(key)
  if cached is not None:
    return cached

  unpack = make_unpacker(u32, *specs, consume_all=consume_all)

  def unpack_versioned(payload):
    got_version, *values = unpack(payload)
    if got_version != version:
      raise ValueError(f"unsupported payload version {got_version}; expected {version}")
    return tuple(values)

  _versioned_unpacker_cache[key] = unpack_versioned
  return unpack_versioned


def decode_as(spec, payload, *, consume_all=True):
  key = (spec, consume_all)
  unpack = _decode_cache.get(key)
  if unpack is None:
    unpack = make_unpacker(spec, consume_all=consume_all)
    _decode_cache[key] = unpack
  (value,) = unpack(payload)
  return value


unpack_as = decode_as


def make_payload() -> bytes:
  raise RuntimeError("make_payload() is only valid inside a packet_payload-decorated method")


def _public_signature(sig):
  return sig.replace(
    parameters=[
      param.replace(annotation=inspect.Signature.empty)
      for param in sig.parameters.values()
    ],
    return_annotation=inspect.Signature.empty,
  )


def _packet_payload_params(sig):
  params = tuple(sig.parameters.values())
  if not params or params[0].name != "self":
    raise TypeError("packet_payload methods must accept self as the first parameter")

  for param in params:
    if param.kind is inspect.Parameter.POSITIONAL_ONLY:
      raise TypeError("packet_payload methods cannot use positional-only parameters")
    if param.kind is inspect.Parameter.VAR_POSITIONAL:
      raise TypeError("packet_payload methods cannot use variadic positional parameters")
    if param.kind is inspect.Parameter.VAR_KEYWORD:
      raise TypeError("packet_payload methods cannot use variadic keyword parameters")

  return params[1:]


def _function_node(method):
  source = textwrap.dedent(inspect.getsource(method))
  module = ast.parse(source)
  for node in module.body:
    if isinstance(node, ast.FunctionDef):
      return node
  raise TypeError("packet_payload can only decorate regular functions")


def _payload_assignment(payload_params):
  return ast.Assign(
    targets=[ast.Name(id="payload", ctx=ast.Store())],
    value=ast.Call(
      func=ast.Name(id="__packet_packer", ctx=ast.Load()),
      args=[ast.Name(id=param.name, ctx=ast.Load()) for param in payload_params],
      keywords=[],
    ),
  )


def _is_make_payload_marker(node):
  if not isinstance(node, ast.Assign):
    return False
  if len(node.targets) != 1:
    return False
  target = node.targets[0]
  if not isinstance(target, ast.Name) or target.id != "payload":
    return False
  if not isinstance(node.value, ast.Call):
    return False
  if node.value.args or node.value.keywords:
    return False
  func = node.value.func
  if isinstance(func, ast.Name):
    return func.id == "make_payload"
  return isinstance(func, ast.Attribute) and func.attr == "make_payload"


def _replace_payload_marker(function_node, payload_params):
  function_node.decorator_list = []
  function_node.returns = None
  for arg in (
    function_node.args.posonlyargs
    + function_node.args.args
    + function_node.args.kwonlyargs
  ):
    arg.annotation = None

  for index, node in enumerate(function_node.body):
    if _is_make_payload_marker(node):
      function_node.body[index] = _payload_assignment(payload_params)
      return function_node

  raise TypeError(f"{function_node.name} must assign payload = make_payload()")

  return function_node


def packet_payload(method=None, *, version: int = 1):
  def decorate(fn):
    sig = inspect.signature(fn)
    payload_params = _packet_payload_params(sig)
    hints = typing.get_type_hints(fn, include_extras=True)
    missing = [param.name for param in payload_params if param.name not in hints]
    if missing:
      raise TypeError(f"{fn.__qualname__} is missing packet annotations for: {', '.join(missing)}")

    packer = make_versioned_packer(*(hints[param.name] for param in payload_params), version=version)
    function_node = _replace_payload_marker(_function_node(fn), payload_params)
    module = ast.Module(body=[function_node], type_ignores=[])
    ast.fix_missing_locations(module)

    namespace = dict(fn.__globals__)
    namespace["__packet_packer"] = packer
    exec(compile(module, fn.__code__.co_filename, "exec"), namespace)
    generated = namespace[fn.__name__]
    generated.__doc__ = fn.__doc__
    generated.__module__ = fn.__module__
    generated.__qualname__ = fn.__qualname__
    generated.__signature__ = _public_signature(sig)
    return generated

  if method is None:
    return decorate
  return decorate(method)
