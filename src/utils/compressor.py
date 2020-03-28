import zlib
import json


def compress_string(s1):
    return zlib.compress(str.encode(s1))


def decompress_string(s1):
    return zlib.decompress(s1).decode("utf-8")


def compress_obj(obj1):
    return compress_string(json.dumps(obj1))


def decompress_obj(obj1):
    return json.loads(decompress_string(obj1))



