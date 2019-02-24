import os
from io import BytesIO
from .errors import Error
from .apply import unpack_size
from .apply import TYPE_NORMAL
from .apply import TYPE_IN_PLACE
from .apply import peek_header_type
from .apply import read_header_normal
from .apply import read_header_in_place
from .apply import PatchReader


def patch_info_normal(fpatch):
    fpatch.seek(0, os.SEEK_END)
    patch_size = fpatch.tell()
    fpatch.seek(0, os.SEEK_SET)

    to_size, compression = read_header_normal(fpatch)
    patch_reader = PatchReader(fpatch, compression)
    to_pos = 0

    number_of_size_bytes = 0
    diff_sizes = []
    extra_sizes = []
    adjustment_sizes = []

    while to_pos < to_size:
        # Diff data.
        size, number_of_bytes = unpack_size(patch_reader)

        if to_pos + size > to_size:
            raise Error("Patch diff data too long.")

        diff_sizes.append(size)
        number_of_size_bytes += number_of_bytes
        patch_reader.decompress(size)
        to_pos += size

        # Extra data.
        size, number_of_bytes = unpack_size(patch_reader)
        number_of_size_bytes += number_of_bytes

        if to_pos + size > to_size:
            raise Error("Patch extra data too long.")

        extra_sizes.append(size)
        patch_reader.decompress(size)
        to_pos += size

        # Adjustment.
        size, number_of_bytes = unpack_size(patch_reader)
        number_of_size_bytes += number_of_bytes
        adjustment_sizes.append(size)

    if not patch_reader.eof:
        raise Error('End of patch not found.')

    return (compression,
            patch_size,
            to_size,
            diff_sizes,
            extra_sizes,
            adjustment_sizes,
            number_of_size_bytes)


def patch_info_in_place(fpatch):
    number_of_segments, from_shift_size = read_header_in_place(fpatch)
    patches = []

    for _ in range(number_of_segments):
        from_offset = unpack_size(fpatch)[0]
        patch_size = unpack_size(fpatch)[0]
        info = patch_info_normal(BytesIO(fpatch.read(patch_size)))
        patches.append((from_offset, patch_size, info))

    return number_of_segments, from_shift_size, patches


def patch_info(fpatch):
    patch_type = peek_header_type(fpatch)

    if patch_type == TYPE_NORMAL:
        return 'normal', patch_info_normal(fpatch)
    elif patch_type == TYPE_IN_PLACE:
        return 'in-place', patch_info_in_place(fpatch)
    else:
        raise Error('Bad patch type.')
