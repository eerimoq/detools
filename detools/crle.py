"""Conditional Run Length Encoding (CRLE) is compresses repeated bytes
with RLE, but leaves other data sequences as is.

"""

import struct
from .errors import Error


MINIMUM_REPEATED_SIZE = 6


class CrleCompressor(object):

    SCATTERED = 0
    REPEATED = 1

    def __init__(self):
        self._data = []

    def compress(self, data):
        self._data.append(data)

        return b''

    def find_repeated_segment(self):
        for offset in range(len(self._data)):
            byte = self._data[offset]
            length = 0

            while ((offset + length < len(self._data))
                   and (byte == self._data[offset + length])):
                length += 1

            if length >= MINIMUM_REPEATED_SIZE:
                return offset, length

        return None, None


    def get_segment(self):
        offset, length = self.find_repeated_segment()

        if offset is None:
            data = self._data
            self._data = b''
            kind = self.SCATTERED
        elif offset > 0:
            data = self._data[:offset]
            self._data = self._data[offset:]
            kind = self.SCATTERED
        else:
            data = self._data[:length]
            self._data = self._data[length:]
            kind = self.REPEATED

        return kind, data

    def compress_one(self):
        if len(self._data) == 0:
            return b''

        kind, data = self.get_segment()
        compressed = struct.pack('B', kind)
        compressed += pack_size(len(data))

        if kind == self.SCATTERED:
            compressed += data
        else:
            compressed += data[:1]

        return compressed

    def flush(self):
        self._data = b''.join(self._data)
        compressed = []

        while True:
            one = self.compress_one()

            if not one:
                break

            compressed.append(one)

        return b''.join(compressed)


class CrleDecompressor(object):

    SCATTERED = 0
    REPEATED = 1

    def __init__(self, number_of_bytes):
        self._number_of_bytes = number_of_bytes
        self._indata = b''
        self._outdata = None
        self._eof = False

    def decompress_all(self):
        outdata = []
        offset = 0

        while offset < self._number_of_bytes:
            kind = self._indata[offset]
            offset += 1

            if kind == self.SCATTERED:
                length, offset = unpack_size(self._indata, offset)
                outdata.append(self._indata[offset:offset + length])
                offset += length
            elif kind == self.REPEATED:
                repetitions, offset = unpack_size(self._indata, offset)
                outdata.append(repetitions * self._indata[offset:offset + 1])
                offset += 1
            else:
                raise Error(
                    'Expected kind scattered(0) or repeated(1), but got {}.'.format(
                        kind))

        self._outdata = b''.join(outdata)

    def decompress(self, data, size):
        """Decompress up to size bytes.

        """

        self._indata += data

        if len(self._indata) == self._number_of_bytes:
            if self._outdata is None:
                self.decompress_all()

        if self._outdata is None:
            data = b''
        else:
            data = self._outdata[:size]
            self._outdata = self._outdata[size:]

            if self._outdata == b'':
                self._eof = True

        return data

    @property
    def needs_input(self):
        return len(self._indata) < self._number_of_bytes

    @property
    def eof(self):
        return self._eof


def pack_size(value):
    if value >= 0x8000000000000000:
        raise Error('Size too big.')

    packed = bytearray()
    packed.append(0)
    packed[0] |= (0x80 | (value & 0x7f))
    value >>= 7

    while value > 0:
        packed.append(0x80 | (value & 0x7f))
        value >>= 7

    packed[-1] &= 0x7f

    return packed


def unpack_size(buf, position):
    byte = 0x80
    value = 0
    offset = 0

    while byte & 0x80:
        byte = buf[position]
        value |= ((byte & 0x7f) << offset)
        offset += 7
        position += 1

    return value, position
