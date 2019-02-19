import os
import struct
from bz2 import BZ2Decompressor
from .errors import Error


class _PatchBZ2Reader(object):

    def __init__(self, fpatch):
        self._decompressor = BZ2Decompressor()
        self._fpatch = fpatch

    def decompress(self, length):
        """Decompress `length` bytes.

        """

        buf = b''

        while len(buf) < length:
            if self._decompressor.eof:
                raise Error('Early end of patch bz2.')

            if self._decompressor.needs_input:
                data = self._fpatch.read(4096)

                if not data:
                    raise Error('Out of patch data.')
            else:
                data = b''

            try:
                buf += self._decompressor.decompress(data, length - len(buf))
            except Exception:
                raise Error('Patch bz2 decompression failed.')

        return buf

    @property
    def eof(self):
        return self._decompressor.eof


def _unpack_i64(buf):
    return struct.unpack('>q', buf)[0]


def _read_header(fpatch):
    header = fpatch.read(16)

    if len(header) != 16:
        raise Error('Failed to read the patch header.')

    magic = header[0:8]

    if magic != b'bsdiff01':
        raise Error(
            "Expected header magic b'bsdiff01', but got {}.".format(magic))

    new_length = _unpack_i64(header[8:16])

    if new_length < 0:
        raise Error('Expected new length >= 0, but got {}.'.format(new_length))

    return new_length


def patch(fold, fpatch, fnew):
    """Apply `fpatch` to `fold` and write the result to `fnew`. All
    arguments are file-like objects.

    """

    new_length = _read_header(fpatch)
    patch_bz2 = _PatchBZ2Reader(fpatch)
    new_pos = 0

    while new_pos < new_length:
        # Diff data.
        length = _unpack_i64(patch_bz2.decompress(8))

        if new_pos + length > new_length:
            raise Error("Patch diff data too long.")

        for _ in range(length):
            byte = patch_bz2.decompress(1)[0]
            byte += fold.read(1)[0]
            byte %= 256
            fnew.write(bytearray([byte]))

        new_pos += length

        # Extra data.
        length = _unpack_i64(patch_bz2.decompress(8))

        if new_pos + length > new_length:
            raise Error("Patch extra data too long.")

        fnew.write(patch_bz2.decompress(length))
        new_pos += length

        # Adjustment.
        length = _unpack_i64(patch_bz2.decompress(8))
        fold.seek(length, os.SEEK_CUR)

    if new_pos != new_length:
        raise Error('New data length mismatch.')

    if not patch_bz2.eof:
        raise Error('End of patch bz2 not found.')
