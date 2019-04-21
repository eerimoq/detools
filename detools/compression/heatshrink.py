"""Heatshrink wrapper.

"""

try:
    from heatshrink.core import Writer
    from heatshrink.core import Reader
    from heatshrink.core import Encoder
except ImportError:
    print('detools: Failed to import heatshrink.')


class HeatshrinkCompressor(object):

    def __init__(self):
        self._encoder = Encoder(Writer(window_sz2=8, lookahead_sz2=7))

    def compress(self, data):
        return self._encoder.fill(data)

    def flush(self):
        return self._encoder.finish()


class HeatshrinkDecompressor(object):

    def __init__(self, number_of_bytes):
        self._number_of_bytes_left = number_of_bytes
        self._data = b''
        self._encoder = Encoder(Reader(window_sz2=8, lookahead_sz2=7))

    def decompress(self, data, size):
        if self._number_of_bytes_left > 0:
            self._data += self._encoder.fill(data)
            self._number_of_bytes_left -= len(data)

        if self._number_of_bytes_left == 0:
            self._data += self._encoder.finish()
            self._number_of_bytes_left = -1

        decompressed = self._data[:size]
        self._data = self._data[size:]

        return decompressed

    @property
    def needs_input(self):
        return self._data == b'' and not self.eof

    @property
    def eof(self):
        return self._number_of_bytes_left == -1 and self._data == b''
