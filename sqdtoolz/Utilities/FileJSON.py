import io
import base64
import zlib
import numpy as np
import json

class SerialiseJSON:
    @staticmethod
    def encode_ndarray(arr: np.ndarray, use_hex=False) -> str:
        """Serialize a NumPy array to a compressed base64 string."""
        buf = io.BytesIO()
        np.save(buf, arr, allow_pickle=False)
        if use_hex:
            return zlib.compress(buf.getvalue()).hex().upper()
        else:
            return base64.b64encode(zlib.compress(buf.getvalue())).decode("ascii")

    def decode_ndarray(data: str, use_hex=False) -> np.ndarray:
        """Deserialize a NumPy array from a compressed hexadecimal string."""
        if use_hex:
            raw = zlib.decompress(bytes.fromhex(data))
        else:
            raw = zlib.decompress(base64.b64decode(data.encode("ascii")))
        return np.load(io.BytesIO(raw), allow_pickle=False)

    @staticmethod    
    def decode_hook(obj):
        if "__type__" in obj:
            if obj["__type__"] == 'numpy.ndarray':
                assert "data" in obj, "If it is a serialised numpy array, there must be a 'data' key with the encoded data."
                return SerialiseJSON.decode_ndarray(obj["data"])
        return obj

class SQDJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        #Inspired by: https://stackoverflow.com/questions/56250514/how-to-tackle-with-error-object-of-type-int32-is-not-json-serializable/56254172
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return {
                "__type__": "numpy.ndarray",
                "encoding": "npy+zlib+base64",
                "data": SerialiseJSON.encode_ndarray(obj)
            }
        return super().default(obj)
