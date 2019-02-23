import os
import struct
from lzma import LZMADecompressor
from .errors import Error


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
        return self._data == b''

    @property
    def eof(self):
        return self._number_of_bytes_left == 0


class _PatchReader(object):

    def __init__(self, fpatch, compression):
        if compression == 'lzma':
            self._decompressor = LZMADecompressor()
        elif compression == 'none':
            position = fpatch.tell()
            fpatch.seek(0, os.SEEK_END)
            length = fpatch.tell()
            fpatch.seek(position, os.SEEK_SET)
            self._decompressor = NoneDecompressor(length - position)
        else:
            raise Error()

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


def _unpack_size(patch_reader):
    byte = patch_reader.decompress(1)[0]
    is_signed = (byte & 0x40)
    value = (byte & 0x3f)
    offset = 6

    while byte & 0x80:
        byte = patch_reader.decompress(1)[0]
        value |= ((byte & 0x7f) << offset)
        offset += 7

    if is_signed:
        value *= -1

    return value, ((offset - 6) / 7 + 1)


def _read_header(fpatch):
    header = fpatch.read(20)

    if len(header) != 20:
        raise Error('Failed to read the patch header.')

    magic = header[0:7]

    if magic != b'detools':
        raise Error(
            "Expected header magic b'detools', but got {}.".format(magic))

    kind = header[7]

    if kind != 48:
        raise Error("Expected kind 48, but got {}.".format(kind))

    compression = header[8:12]

    try:
        compression = compression.decode('ascii')
    except UnicodeDecodeError:
        raise Error(
            'Failed to decode the compression field in the header (got {}).'.format(
                compression))

    if compression not in ['lzma', 'none']:
        raise Error(
            "Expected compression 'lzma' or 'none', but got '{}'.".format(
                compression))

    to_size = struct.unpack('>Q', header[12:20])[0]

    return to_size, compression


def apply_patch(ffrom, fpatch, fto):
    """Apply `fpatch` to `ffrom` and write the result to `fto`. All
    arguments are file-like objects.

    """

    to_size, compression = _read_header(fpatch)
    patch_reader = _PatchReader(fpatch, compression)
    to_pos = 0

    while to_pos < to_size:
        # Diff data.
        size = _unpack_size(patch_reader)[0]

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
        size = _unpack_size(patch_reader)[0]

        if to_pos + size > to_size:
            raise Error("Patch extra data too long.")

        fto.write(patch_reader.decompress(size))
        to_pos += size

        # Adjustment.
        size = _unpack_size(patch_reader)[0]
        ffrom.seek(size, os.SEEK_CUR)

    if to_pos != to_size:
        raise Error('To data size mismatch.')

    if not patch_reader.eof:
        raise Error('End of patch not found.')


def patch_info(fpatch):
    fpatch.seek(0, os.SEEK_END)
    patch_size = fpatch.tell()
    fpatch.seek(0, os.SEEK_SET)

    to_size, compression = _read_header(fpatch)
    patch_reader = _PatchReader(fpatch, compression)
    to_pos = 0

    number_of_size_bytes = 0
    diff_sizes = []
    extra_sizes = []
    adjustment_sizes = []

    while to_pos < to_size:
        # Diff data.
        size, number_of_bytes = _unpack_size(patch_reader)

        if to_pos + size > to_size:
            raise Error("Patch diff data too long.")

        diff_sizes.append(size)
        number_of_size_bytes += number_of_bytes
        patch_reader.decompress(size)
        to_pos += size

        # Extra data.
        size, number_of_bytes = _unpack_size(patch_reader)
        number_of_size_bytes += number_of_bytes

        if to_pos + size > to_size:
            raise Error("Patch extra data too long.")

        extra_sizes.append(size)
        patch_reader.decompress(size)
        to_pos += size

        # Adjustment.
        size, number_of_bytes = _unpack_size(patch_reader)
        number_of_size_bytes += number_of_bytes
        adjustment_sizes.append(size)

    if to_pos != to_size:
        raise Error('To data size mismatch.')

    if not patch_reader.eof:
        raise Error('End of patch not found.')

    return (compression,
            patch_size,
            to_size,
            diff_sizes,
            extra_sizes,
            adjustment_sizes,
            number_of_size_bytes)
