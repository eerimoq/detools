import os
import struct
from lzma import LZMADecompressor
from .errors import Error


class _PatchReader(object):

    def __init__(self, fpatch):
        self._decompressor = LZMADecompressor()
        self._fpatch = fpatch

    def decompress(self, size):
        """Decompress `size` bytes.

        """

        buf = b''

        while len(buf) < size:
            if self._decompressor.eof:
                raise Error('Early end of patch data.')

            if self._decompressor.needs_input:
                data = self._fpatch.read(4096)

                if not data:
                    raise Error('Out of patch data.')
            else:
                data = b''

            try:
                buf += self._decompressor.decompress(data, size - len(buf))
            except Exception:
                raise Error('Patch decompression failed.')

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

    if magic != b'detools0':
        raise Error(
            "Expected header magic b'detools0', but got {}.".format(magic))

    to_size = _unpack_i64(header[8:16])

    if to_size < 0:
        raise Error('Expected to size >= 0, but got {}.'.format(to_size))

    return to_size


def apply_patch(ffrom, fpatch, fto):
    """Apply `fpatch` to `ffrom` and write the result to `fto`. All
    arguments are file-like objects.

    """

    to_size = _read_header(fpatch)
    patch_reader = _PatchReader(fpatch)
    to_pos = 0

    while to_pos < to_size:
        # Diff data.
        size = _unpack_i64(patch_reader.decompress(8))

        if to_pos + size > to_size:
            raise Error("Patch diff data too long.")

        offset = 0

        while offset < size:
            chunk_size = min(size - offset, 4096)
            offset += chunk_size
            patch_data = patch_reader.decompress(chunk_size)
            from_data = ffrom.read(chunk_size)
            fto.write(bytearray(
                (pb + ob) & 0xff for pb, ob in zip(patch_data, from_data)
            ))

        to_pos += size

        # Extra data.
        size = _unpack_i64(patch_reader.decompress(8))

        if to_pos + size > to_size:
            raise Error("Patch extra data too long.")

        fto.write(patch_reader.decompress(size))
        to_pos += size

        # Adjustment.
        size = _unpack_i64(patch_reader.decompress(8))
        ffrom.seek(size, os.SEEK_CUR)

    if to_pos != to_size:
        raise Error('To data size mismatch.')

    if not patch_reader.eof:
        raise Error('End of patch not found.')
