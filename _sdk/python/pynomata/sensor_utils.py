from typing import Annotated
from typing import overload

import zenoh
import numpy as np

from .common_types import *
from .packet import *

_DATA_TYPE_TO_NP_DTYPE = {
  DataType.UINT8:   np.dtype(np.uint8),
  DataType.UINT16:  np.dtype(np.uint16),
  DataType.UINT32:  np.dtype(np.uint32),
  DataType.UINT64:  np.dtype(np.uint64),
  DataType.INT8:    np.dtype(np.int8),
  DataType.INT16:   np.dtype(np.int16),
  DataType.INT32:   np.dtype(np.int32),
  DataType.INT64:   np.dtype(np.int64),
  DataType.FLOAT16: np.dtype(np.float16),
  DataType.FLOAT32: np.dtype(np.float32),
  DataType.FLOAT64: np.dtype(np.float64),
  DataType.BOOL:    np.dtype(np.bool_),
}

def to_np_dtype(dt: DataType) -> np.dtype:
  try:
    return _DATA_TYPE_TO_NP_DTYPE[DataType(dt)]
  except KeyError as e:
    raise ValueError(f"Unsupported DataType: {dt}") from e
