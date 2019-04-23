import os
import struct
from lzma import LZMADecompressor
from bz2 import BZ2Decompressor
import bitstruct
from .errors import Error
from .compression.crle import CrleDecompressor
from .compression.none import NoneDecompressor
from .compression.heatshrink import HeatshrinkDecompressor
from .common import COMPRESSION_NONE
from .common import COMPRESSION_LZMA
from .common import COMPRESSION_CRLE
from .common import COMPRESSION_BZ2
from .common import COMPRESSION_HEATSHRINK
from .common import PATCH_TYPE_NORMAL
from .common import PATCH_TYPE_IN_PLACE
from .common import format_bad_compression_string
from .common import format_bad_compression_number
from .common import file_size
from .common import unpack_size
from .data_format import create_readers


class PatchReader(object):

    def __init__(self, fpatch, compression):
        if compression == 'lzma':
            self._decompressor = LZMADecompressor()
        elif compression == 'bz2':
            self._decompressor = BZ2Decompressor()
        elif compression == 'crle':
            self._decompressor = CrleDecompressor(patch_data_length(fpatch))
        elif compression == 'none':
            self._decompressor = NoneDecompressor(patch_data_length(fpatch))
        elif compression == 'heatshrink':
            self._decompressor = HeatshrinkDecompressor(patch_data_length(fpatch))
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


def iter_chunks(patch_reader, to_pos, to_size, message):
    size = unpack_size(patch_reader)

    if to_pos + size > to_size:
        raise Error(message)

    offset = 0

    while offset < size:
        chunk_size = min(size - offset, 4096)
        offset += chunk_size
        patch_data = patch_reader.decompress(chunk_size)

        yield chunk_size, patch_data


def iter_diff_chunks(patch_reader, to_pos, to_size):
    return iter_chunks(patch_reader,
                       to_pos,
                       to_size,
                       "Patch diff data too long.")


def iter_extra_chunks(patch_reader, to_pos, to_size):
    return iter_chunks(patch_reader,
                       to_pos,
                       to_size,
                       "Patch extra data too long.")


def patch_data_length(fpatch):
    return file_size(fpatch) - fpatch.tell()


def unpack_header(data):
    return bitstruct.unpack('p1u3u4', data)


def convert_compression(compression):
    if compression == COMPRESSION_NONE:
        compression = 'none'
    elif compression == COMPRESSION_LZMA:
        compression = 'lzma'
    elif compression == COMPRESSION_CRLE:
        compression = 'crle'
    elif compression == COMPRESSION_BZ2:
        compression = 'bz2'
    elif compression == COMPRESSION_HEATSHRINK:
        compression = 'heatshrink'
    else:
        raise Error(format_bad_compression_number(compression))

    return compression


def read_header_normal(fpatch):
    """Read a normal header.

    """

    header = fpatch.read(1)

    if len(header) != 1:
        raise Error('Failed to read the patch header.')

    patch_type, compression  = unpack_header(header)

    if patch_type != PATCH_TYPE_NORMAL:
        raise Error("Expected patch type 0, but got {}.".format(patch_type))

    compression = convert_compression(compression)
    to_size = unpack_size(fpatch)

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
    memory_size = unpack_size(fpatch)
    segment_size = unpack_size(fpatch)
    shift_size = unpack_size(fpatch)
    from_size = unpack_size(fpatch)
    to_size = unpack_size(fpatch)

    return compression, memory_size, segment_size, shift_size, from_size, to_size


def offtin(data):
    x = struct.unpack('<Q', data)[0]

    if x & (1 << 63):
        x &= ~(1 << 63)
        x *= -1

    return x


def read_header_bsdiff(fpatch):
    """Read a bsdiff header.

    """

    magic = fpatch.read(8)

    if magic != b'BSDIFF40':
        raise Error(
            "Expected magic 'BSDIFF40', but got '{}'.".format(
                magic.decode('latin-1')))

    ctrl_size = offtin(fpatch.read(8))
    diff_size = offtin(fpatch.read(8))
    to_size = offtin(fpatch.read(8))

    return ctrl_size, diff_size, to_size


def shift_memory(fmem, memory_size, shift_size, from_size):
    """Shift given memory.

    """

    size = file_size(fmem)

    if size < memory_size:
        raise Error(
            'Expected memory size of at least {} bytes, but got {}.'.format(
                memory_size,
                size))

    fmem.seek(0, os.SEEK_SET)
    from_data = fmem.read(from_size)
    fmem.seek(shift_size, os.SEEK_SET)
    fmem.write(from_data[:memory_size - shift_size])


def apply_patch_in_place_segment(fmem,
                                 patch_reader,
                                 to_offset,
                                 to_size,
                                 from_offset):
    """Apply given in-place segment patch.

    """

    dfpatch_size = unpack_size(patch_reader)

    if dfpatch_size > 0:
        raise NotImplementedError()

    to_pos = 0

    while to_pos < to_size:
        # Diff data.
        for chunk_size, patch_data in iter_diff_chunks(patch_reader,
                                                       to_pos,
                                                       to_size):
            fmem.seek(from_offset, os.SEEK_SET)
            from_data = fmem.read(chunk_size)
            from_offset += chunk_size
            fmem.seek(to_offset + to_pos, os.SEEK_SET)
            fmem.write(bytearray(
                (pb + fb) & 0xff for pb, fb in zip(patch_data, from_data)
            ))
            to_pos += chunk_size

        # Extra data.
        fmem.seek(to_offset + to_pos, os.SEEK_SET)

        for chunk_size, patch_data in iter_extra_chunks(patch_reader,
                                                        to_pos,
                                                        to_size):
            fmem.write(patch_data)
            to_pos += chunk_size

        # Adjustment.
        from_offset += unpack_size(patch_reader)


def create_data_format_readers(patch_reader, ffrom, to_size):
    dfpatch_size = unpack_size(patch_reader)

    if dfpatch_size > 0:
        data_format = unpack_size(patch_reader)
        patch = patch_reader.decompress(dfpatch_size)
        dfdiff, ffrom = create_readers(data_format, ffrom, patch, to_size)

        # with open('data-format-from-apply.bin', 'wb') as fout:
        #     fout.write(file_read(ffrom))

        ffrom.seek(0)
    else:
        dfdiff = None

    return dfdiff, ffrom


def apply_patch(ffrom, fpatch, fto):
    """Apply given normal patch `fpatch` to `ffrom` to create
    `fto`. Returns the size of the created to-data.

    All arguments are file-like objects.

    >>> ffrom = open('foo.mem', 'rb')
    >>> fpatch = open('foo.patch', 'rb')
    >>> fto = open('foo.new', 'wb')
    >>> apply_patch(ffrom, fpatch, fto)
    2780

    """

    compression, to_size = read_header_normal(fpatch)

    if to_size == 0:
        return to_size

    patch_reader = PatchReader(fpatch, compression)
    dfdiff, ffrom = create_data_format_readers(patch_reader, ffrom, to_size)
    to_pos = 0

    while to_pos < to_size:
        # Diff data.
        for chunk_size, patch_data in iter_diff_chunks(patch_reader,
                                                       to_pos,
                                                       to_size):
            from_data = ffrom.read(chunk_size)

            if dfdiff is not None:
                dfdiff_data = dfdiff.read(chunk_size)
                data = bytearray(
                    (pb + fb + db) & 0xff for pb, fb, db in zip(patch_data,
                                                                from_data,
                                                                dfdiff_data)
                )
            else:
                data = bytearray(
                    (pb + fb) & 0xff for pb, fb in zip(patch_data, from_data)
                )

            fto.write(data)
            to_pos += chunk_size

        # Extra data.
        for chunk_size, patch_data in iter_extra_chunks(patch_reader,
                                                        to_pos,
                                                        to_size):
            if dfdiff is not None:
                dfdiff_data = dfdiff.read(chunk_size)
                data = bytearray(
                    (dd + db) & 0xff for dd, db in zip(patch_data, dfdiff_data)
                )
            else:
                data = patch_data

            fto.write(data)
            to_pos += chunk_size

        # Adjustment.
        size = unpack_size(patch_reader)
        ffrom.seek(size, os.SEEK_CUR)

    if not patch_reader.eof:
        raise Error('End of patch not found.')

    return to_size


def apply_patch_in_place(fmem, fpatch):
    """Apply given in-place patch `fpatch` to `fmem`. Returns the size of
    the created to-data.

    Both arguments are file-like objects.

    >>> fmem = open('foo.mem', 'r+b')
    >>> fpatch = open('foo-in-place.patch', 'rb')
    >>> apply_patch_in_place(fmem, fpatch)
    2780

    """

    (compression,
     memory_size,
     segment_size,
     shift_size,
     from_size,
     to_size) = read_header_in_place(fpatch)

    if to_size > 0:
        patch_reader = PatchReader(fpatch, compression)
        shift_memory(fmem, memory_size, shift_size, from_size)

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

    return to_size


def apply_patch_bsdiff(ffrom, fpatch, fto):
    """Apply given bsdiff patch `fpatch` to `ffrom` to create
    `fto`. Returns the size of the created to-data.

    All arguments are file-like objects.

    >>> ffrom = open('foo.mem', 'rb')
    >>> fpatch = open('foo-bsdiff.patch', 'rb')
    >>> fto = open('foo.new', 'wb')
    >>> apply_patch_bsdiff(ffrom, fpatch, fto)
    2780

    """

    ctrl_size, diff_size, to_size = read_header_bsdiff(fpatch)

    ctrl_decompressor = BZ2Decompressor()
    diff_decompressor = BZ2Decompressor()
    extra_decompressor = BZ2Decompressor()

    ctrl_decompressor.decompress(fpatch.read(ctrl_size), 0)
    diff_decompressor.decompress(fpatch.read(diff_size), 0)
    extra_decompressor.decompress(fpatch.read(), 0)

    to_pos = 0

    while to_pos < to_size:
        # Control data.
        diff_size = offtin(ctrl_decompressor.decompress(b'', 8))
        extra_size = offtin(ctrl_decompressor.decompress(b'', 8))
        adjustment = offtin(ctrl_decompressor.decompress(b'', 8))

        # Diff data.
        if to_pos + diff_size > to_size:
            raise Error("Patch diff data too long.")

        diff_data = diff_decompressor.decompress(b'', diff_size)
        from_data = ffrom.read(diff_size)
        data = bytearray(
            (db + fb) & 0xff for db, fb in zip(diff_data, from_data)
        )
        fto.write(data)
        to_pos += diff_size

        # Extra data.
        if to_pos + extra_size > to_size:
            raise Error("Patch extra data too long.")

        extra_data = extra_decompressor.decompress(b'', extra_size)
        fto.write(extra_data)
        to_pos += extra_size

        # Adjustment.
        ffrom.seek(adjustment, os.SEEK_CUR)

    if not ctrl_decompressor.eof:
        raise Error('End of control data not found.')

    if not diff_decompressor.eof:
        raise Error('End of diff data not found.')

    if not extra_decompressor.eof:
        raise Error('End of extra data not found.')

    return to_size


def apply_patch_filenames(fromfile, patchfile, tofile):
    """Same as :func:`~detools.apply_patch()`, but with filenames instead
    of file-like objects.

    >>> apply_patch_filenames('foo.old', 'foo.patch', 'foo.new')
    2780

    """

    with open(fromfile, 'rb') as ffrom:
        with open(patchfile, 'rb') as fpatch:
            with open(tofile, 'wb') as fto:
                return apply_patch(ffrom, fpatch, fto)


def apply_patch_in_place_filenames(memfile, patchfile):
    """Same as :func:`~detools.apply_patch_in_place()`, but with filenames
    instead of file-like objects.

    >>> apply_patch_in_place_filenames('foo.mem', 'foo-in-place.patch')
    2780

    """

    with open(memfile, 'r+b') as fmem:
        with open(patchfile, 'rb') as fpatch:
            return apply_patch_in_place(fmem, fpatch)


def apply_patch_bsdiff_filenames(fromfile, patchfile, tofile):
    """Same as :func:`~detools.apply_patch_bsdiff()`, but with filenames
    instead of file-like objects.

    >>> apply_patch_bsdiff_filenames('foo.old', 'foo-bsdiff.patch', 'foo.new')
    2780

    """

    with open(fromfile, 'rb') as ffrom:
        with open(patchfile, 'rb') as fpatch:
            with open(tofile, 'wb') as fto:
                return apply_patch_bsdiff(ffrom, fpatch, fto)
