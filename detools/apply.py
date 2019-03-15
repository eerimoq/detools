import os
from lzma import LZMADecompressor
import bitstruct
from .errors import Error
from .crle import CrleDecompressor
from .none import NoneDecompressor
from .common import PATCH_TYPE_NORMAL
from .common import PATCH_TYPE_IN_PLACE
from .common import format_bad_compression_string
from .common import format_bad_compression_number


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
            raise Error(format_bad_compression_string(compression))

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
    try:
        byte = fin.read(1)[0]
    except IndexError:
        raise Error('Failed to read first size byte.')

    is_signed = (byte & 0x40)
    value = (byte & 0x3f)
    offset = 6

    while byte & 0x80:
        try:
            byte = fin.read(1)[0]
        except IndexError:
            raise Error('Failed to read consecutive size byte.')

        value |= ((byte & 0x7f) << offset)
        offset += 7

    if is_signed:
        value *= -1

    return value, ((offset - 6) / 7 + 1)


def unpack_header(data):
    return bitstruct.unpack('p1u3u4', data)


def convert_compression(compression):
    if compression == 0:
        compression = 'none'
    elif compression == 1:
        compression = 'lzma'
    elif compression == 2:
        compression = 'crle'
    else:
        raise Error(format_bad_compression_number(compression))

    return compression


def peek_header_type(fpatch):
    position = fpatch.tell()
    header = fpatch.read(1)
    fpatch.seek(position, os.SEEK_SET)

    if len(header) != 1:
        raise Error('Failed to read the patch header.')

    return unpack_header(header)[0]


def read_header_normal(fpatch):
    """Read a normal header.

    """

    header = fpatch.read(1)

    if len(header) != 1:
        raise Error('Failed to read the patch header.')

    patch_type, compression = unpack_header(header)

    if patch_type != PATCH_TYPE_NORMAL:
        raise Error("Expected patch type 0, but got {}.".format(patch_type))

    compression = convert_compression(compression)
    to_size = unpack_size(fpatch)[0]

    return compression, to_size


def read_header_in_place(fpatch):
    """Read an in-place header.

    """

    header = fpatch.read(1)

    if len(header) != 1:
        raise Error('Failed to read the patch header.')

    patch_type, compression = unpack_header(header)

    if patch_type != PATCH_TYPE_IN_PLACE:
        raise Error("Expected patch type 1, but got {}.".format(patch_type))

    compression = convert_compression(compression)
    memory_size = unpack_size(fpatch)[0]
    segment_size = unpack_size(fpatch)[0]
    shift_size = unpack_size(fpatch)[0]
    from_size = unpack_size(fpatch)[0]
    to_size = unpack_size(fpatch)[0]

    return compression, memory_size, segment_size, shift_size, from_size, to_size


def apply_patch_normal_inner(ffrom, patch_reader, fto, to_size):
    """Apply given normal patch.

    """

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
                (pb + fb) & 0xff for pb, fb in zip(patch_data, from_data)
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


def apply_patch_normal(ffrom, fpatch, fto):
    """Apply given normal patch.

    """

    compression, to_size = read_header_normal(fpatch)

    if to_size == 0:
        return

    patch_reader = PatchReader(fpatch, compression)

    apply_patch_normal_inner(ffrom, patch_reader, fto, to_size)

    if not patch_reader.eof:
        raise Error('End of patch not found.')


def apply_patch_in_place_segment(fmem,
                                 patch_reader,
                                 to_offset,
                                 to_size,
                                 from_offset):
    """Apply given in-place segment patch.

    """

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
            fmem.seek(from_offset, os.SEEK_SET)
            from_data = fmem.read(chunk_size)
            from_offset += chunk_size
            fmem.seek(to_offset + to_pos, os.SEEK_SET)
            fmem.write(bytearray(
                (pb + fb) & 0xff for pb, fb in zip(patch_data, from_data)
            ))
            to_pos += chunk_size

        # Extra data.
        size = unpack_size(patch_reader)[0]

        if to_pos + size > to_size:
            raise Error("Patch extra data too long.")

        fmem.seek(to_offset + to_pos, os.SEEK_SET)
        fmem.write(patch_reader.decompress(size))
        to_pos += size

        # Adjustment.
        from_offset += unpack_size(patch_reader)[0]


def shift_mem(fmem, memory_size, shift_size, from_size):
    """Shift given memory.

    """

    fmem.seek(0, os.SEEK_END)
    size = fmem.tell()

    if size < memory_size:
        fmem.write((memory_size - size) * b'\xff')

    fmem.seek(0, os.SEEK_SET)
    from_data = fmem.read(from_size)
    fmem.seek(shift_size, os.SEEK_SET)
    fmem.write(from_data[:memory_size - shift_size])


def apply_patch_in_place(fmem, fpatch):
    """Apply given in-place patch.

    """

    (compression,
     memory_size,
     segment_size,
     shift_size,
     from_size,
     to_size) = read_header_in_place(fpatch)

    if to_size > 0:
        patch_reader = PatchReader(fpatch, compression)
        shift_mem(fmem, memory_size, shift_size, from_size)

        for i, to_pos in enumerate(range(0, to_size, segment_size)):
            from_offset = max(segment_size * (i + 1), shift_size)
            segment_to_size = min(segment_size, to_size - to_pos)
            apply_patch_in_place_segment(fmem,
                                         patch_reader,
                                         to_pos,
                                         segment_to_size,
                                         from_offset)

        if not patch_reader.eof:
            raise Error('End of patch not found.')

    fmem.truncate(to_size)


def apply_patch(ffrom, fpatch, fto):
    """Apply `fpatch` to `ffrom` and write the result to `fto`. All
    arguments are file-like objects.

    """

    apply_patch_normal(ffrom, fpatch, fto)
