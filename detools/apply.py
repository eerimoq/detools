import os
import struct
from lzma import LZMADecompressor
from io import BytesIO
from .errors import Error
from .crle import CrleDecompressor
from .none import NoneDecompressor


TYPE_NORMAL    = ord('0')
TYPE_IN_PLACE  = ord('1')


def patch_length(fpatch):
    position = fpatch.tell()
    fpatch.seek(0, os.SEEK_END)
    length = fpatch.tell()
    fpatch.seek(position, os.SEEK_SET)

    return length - position


class PatchReader(object):

    def __init__(self, fpatch, compression):
        if compression == 'lzma':
            self._decompressor = LZMADecompressor()
        elif compression == 'crle':
            self._decompressor = CrleDecompressor(patch_length(fpatch))
        elif compression == 'none':
            self._decompressor = NoneDecompressor(patch_length(fpatch))
        else:
            raise Error(compression)

        self._fpatch = fpatch

    def read(self, size):
        return self.decompress(size)

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


def unpack_size(fin):
    byte = fin.read(1)[0]
    is_signed = (byte & 0x40)
    value = (byte & 0x3f)
    offset = 6

    while byte & 0x80:
        byte = fin.read(1)[0]
        value |= ((byte & 0x7f) << offset)
        offset += 7

    if is_signed:
        value *= -1

    return value, ((offset - 6) / 7 + 1)


def peek_header_type(fpatch):
    position = fpatch.tell()
    header = fpatch.read(8)
    fpatch.seek(position, os.SEEK_SET)

    if len(header) != 8:
        raise Error('Failed to read the patch header.')

    magic = header[0:7]

    if magic != b'detools':
        raise Error(
            "Expected header magic b'detools', but got {}.".format(magic))

    return header[7]


def read_header_normal(fpatch):
    """Read a normal header.

    """

    header = fpatch.read(20)

    if len(header) != 20:
        raise Error('Failed to read the patch header.')

    magic = header[0:7]

    if magic != b'detools':
        raise Error(
            "Expected header magic b'detools', but got {}.".format(magic))

    patch_type = header[7]

    if patch_type != 48:
        raise Error("Expected patch type 48, but got {}.".format(patch_type))

    compression = header[8:12]

    try:
        compression = compression.decode('ascii')
    except UnicodeDecodeError:
        raise Error(
            'Failed to decode the compression field in the header (got {}).'.format(
                compression))

    if compression not in ['lzma', 'crle', 'none']:
        raise Error(
            "Expected compression 'lzma' or 'none', but got '{}'.".format(
                compression))

    to_size = struct.unpack('>Q', header[12:20])[0]

    return to_size, compression


def read_header_in_place(fpatch):
    """Read an in-place header.

    """

    header = fpatch.read(8)

    if len(header) != 8:
        raise Error('Failed to read the patch header.')

    magic = header[0:7]

    if magic != b'detools':
        raise Error(
            "Expected header magic b'detools', but got {}.".format(magic))

    patch_type = header[7]

    if patch_type != 49:
        raise Error("Expected patch type 49, but got {}.".format(patch_type))

    number_of_segments = unpack_size(fpatch)[0]
    shift_size = unpack_size(fpatch)[0]

    return number_of_segments, shift_size


def apply_patch_normal(ffrom, fpatch, fto):
    """Apply given normal patch.

    """

    to_size, compression = read_header_normal(fpatch)
    patch_reader = PatchReader(fpatch, compression)
    to_pos = 0

    while to_pos < to_size:
        # Diff data.
        size = unpack_size(patch_reader)[0]

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
        size = unpack_size(patch_reader)[0]

        if to_pos + size > to_size:
            raise Error("Patch extra data too long.")

        fto.write(patch_reader.decompress(size))
        to_pos += size

        # Adjustment.
        size = unpack_size(patch_reader)[0]
        ffrom.seek(size, os.SEEK_CUR)

    if not patch_reader.eof:
        raise Error('End of patch not found.')


def apply_patch_in_place(ffrom, fpatch, fto):
    """Apply given in-place patch.

    """

    number_of_segments, _ = read_header_in_place(fpatch)

    for _ in range(number_of_segments):
        from_offset = unpack_size(fpatch)[0]
        patch_size = unpack_size(fpatch)[0]

        ffrom.seek(from_offset, os.SEEK_SET)
        apply_patch_normal(ffrom,
                           BytesIO(fpatch.read(patch_size)),
                           fto)


def apply_patch(ffrom, fpatch, fto):
    """Apply `fpatch` to `ffrom` and write the result to `fto`. All
    arguments are file-like objects.

    """

    patch_type = peek_header_type(fpatch)

    if patch_type == TYPE_NORMAL:
        apply_patch_normal(ffrom, fpatch, fto)
    elif patch_type == TYPE_IN_PLACE:
        apply_patch_in_place(ffrom, fpatch, fto)
    else:
        raise Error(
            "Expected patch type {} or {}, but got {}.".format(
                TYPE_NORMAL,
                TYPE_IN_PLACE,
                patch_type))
