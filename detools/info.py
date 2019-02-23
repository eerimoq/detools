import os
from .errors import Error
from .apply import unpack_size
from .apply import read_header
from .apply import PatchReader


def patch_info(fpatch):
    fpatch.seek(0, os.SEEK_END)
    patch_size = fpatch.tell()
    fpatch.seek(0, os.SEEK_SET)

    to_size, compression = read_header(fpatch)
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
