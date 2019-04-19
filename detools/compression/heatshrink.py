class HeatshrinkCompressor(object):

    def compress(self, data):
        raise NotImplementedError()

    def flush(self):
        raise NotImplementedError()


class HeatshrinkDecompressor(object):

    def __init__(self, number_of_bytes):
        raise NotImplementedError()

    def decompress(self, data, size):
        raise NotImplementedError()

    @property
    def needs_input(self):
        raise NotImplementedError()

    @property
    def eof(self):
        raise NotImplementedError()
