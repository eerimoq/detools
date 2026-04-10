"""Conditional Run Length Encoding (CRLE) compresses repeated bytes
with RLE, but leaves other data sequences as is.

It compresses diffs fairly well, but extras poorly. Not very useful in
general.

"""

import struct
from ..errors import Error


MINIMUM_REPEATED_SIZE = 6

SCATTERED = 0
REPEATED = 1


class CrleCompressor(object):

    def __init__(self):
        self._data = b''
        self._flushing = False
        self._number_of_compressed_bytes = 0

    def compress(self, data):
        """Compress `data` and return any compressed data.

        """

        self._data += data

        return self.compress_segment()

    def flush(self):
        """Compress and return remaining data.

        """

        if self._number_of_compressed_bytes == len(self._data) == 0:
            compressed = struct.pack('B', SCATTERED)
            compressed += pack_size(0)
        else:
            self._flushing = True
            compressed = []

            while True:
                chunk = self.compress_segment()

                if not chunk:
                    break

                compressed.append(chunk)

            compressed = b''.join(compressed)

        return compressed

    def find_repeated_segment(self):
        """Find the first repeated segment in the data and return its offset
        and length. Return ``(None, None)`` if no repeated segment was
        found.

        """

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
        """Get a segment of scattered or repeated data. Returns the segment
        kind and data. Returns ``(None, None)`` if no segment was
        found.

        """

        offset, length = self.find_repeated_segment()

        if offset is None:
            if self._flushing:
                kind = SCATTERED
                data = self._data
                self._data = b''
            else:
                kind = None
                data = None
        elif offset > 0:
            data = self._data[:offset]
            self._data = self._data[offset:]
            kind = SCATTERED
        elif offset + length < len(self._data) or self._flushing:
            data = self._data[:length]
            self._data = self._data[length:]
            kind = REPEATED
        else:
            kind = None
            data = None

        return kind, data

    def compress_segment(self):
        """Compress one segment and return it.

        """

        if len(self._data) == 0:
            return b''

        kind, data = self.get_segment()

        if kind is None:
            return b''

        compressed = struct.pack('B', kind)
        compressed += pack_size(len(data))

        if kind == SCATTERED:
            compressed += data
        else:
            compressed += data[:1]

        self._number_of_compressed_bytes += len(compressed)

        return compressed


class CrleDecompressor(object):

    def __init__(self, number_of_bytes):
        self._number_of_indata_bytes_left = number_of_bytes
        self._indata = b''
        self._outdata = b''
        self._number_of_scattered_bytes_left = 0
        self._number_of_repeated_bytes_left = 0
        self._repeated_byte = b''

    def decompress(self, data, size):
        """Decompress up to size bytes.

        """

        if self.eof:
            raise Error('Already at end of stream.')

        if len(data) > self._number_of_indata_bytes_left:
            data = data[:self._number_of_indata_bytes_left]

        self._indata += data
        self._number_of_indata_bytes_left -= len(data)
        target_size = max(size, 1)

        while len(self._outdata) < target_size:
            previous_state = (
                len(self._indata),
                self._number_of_scattered_bytes_left,
                self._number_of_repeated_bytes_left
            )

            try:
                chunk = self.decompress_segment(target_size - len(self._outdata))
            except IndexError:
                break

            self._outdata += chunk

            if previous_state == (
                    len(self._indata),
                    self._number_of_scattered_bytes_left,
                    self._number_of_repeated_bytes_left):
                break

        data = self._outdata[:size]
        self._outdata = self._outdata[size:]

        return data

    @property
    def needs_input(self):
        return not self.eof and not self._can_make_progress_without_input()

    @property
    def eof(self):
        return (self._number_of_indata_bytes_left == 0
                and self._number_of_scattered_bytes_left == 0
                and self._number_of_repeated_bytes_left == 0
                and len(self._outdata) == 0
                and len(self._indata) == 0)

    def _can_make_progress_without_input(self):
        if len(self._outdata) > 0:
            return True

        if self._number_of_repeated_bytes_left > 0:
            return True

        if self._number_of_scattered_bytes_left > 0:
            return len(self._indata) > 0

        if len(self._indata) == 0:
            return False

        kind = self._indata[0]

        if kind == SCATTERED:
            try:
                length, offset = unpack_size(self._indata, 1)
            except IndexError:
                return False

            return length == 0 or len(self._indata) > offset
        elif kind == REPEATED:
            try:
                _, offset = unpack_size(self._indata, 1)
            except IndexError:
                return False

            return len(self._indata) >= offset + 1
        else:
            return True

    def decompress_segment(self, size):
        """Try to decompress a segment. Raises IndexError if not enough data
        is available..

        """

        if self._number_of_repeated_bytes_left > 0:
            repetitions = min(size, self._number_of_repeated_bytes_left)
            self._number_of_repeated_bytes_left -= repetitions

            return repetitions * self._repeated_byte

        if self._number_of_scattered_bytes_left > 0:
            if len(self._indata) == 0:
                raise IndexError

            length = min(size, len(self._indata), self._number_of_scattered_bytes_left)
            data = self._indata[:length]
            self._indata = self._indata[length:]
            self._number_of_scattered_bytes_left -= length

            return data

        if len(self._indata) == 0:
            raise IndexError

        kind = self._indata[0]

        if kind == SCATTERED:
            total_length, offset = unpack_size(self._indata, 1)

            if len(self._indata) < offset:
                raise IndexError

            available = len(self._indata) - offset

            if total_length == 0:
                self._indata = self._indata[offset:]

                return b''

            if available == 0:
                raise IndexError

            length = min(size, total_length, available)
            data = self._indata[offset:offset + length]
            self._indata = self._indata[offset + length:]
            self._number_of_scattered_bytes_left = total_length - length

            return data
        elif kind == REPEATED:
            repetitions, offset = unpack_size(self._indata, 1)

            if len(self._indata) < offset + 1:
                raise IndexError

            self._repeated_byte = self._indata[offset:offset + 1]
            self._indata = self._indata[offset + 1:]

            if repetitions == 0:
                return b''

            length = min(size, repetitions)
            self._number_of_repeated_bytes_left = repetitions - length

            return length * self._repeated_byte
        else:
            raise Error(
                'Expected kind scattered(0) or repeated(1), but got {}.'.format(
                    kind))


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
