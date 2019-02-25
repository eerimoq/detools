import os
import struct
from lzma import LZMACompressor
from io import BytesIO
from .errors import Error
from .crle import CrleCompressor


class NoneCompressor(object):

    def compress(self, data):
        return data

    def flush(self):
        return b''


class NoneDecompressor(object):

    def __init__(self, number_of_bytes):
        self._number_of_bytes_left = number_of_bytes
        self._data = b''

    def decompress(self, data, size):
        self._data += data
        decompressed = self._data[:size]
        self._data = self._data[size:]

        self._number_of_bytes_left -= len(decompressed)

        if self._number_of_bytes_left < 0:
            raise Error('Out of data to decompress.')

        return decompressed

    @property
    def needs_input(self):
        return self._data == b'' and not self.eof

    @property
    def eof(self):
        return self._number_of_bytes_left == 0
