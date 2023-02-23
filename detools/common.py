import os
import struct
from io import BytesIO
import bitstruct
from .errors import Error
from .bsdiff import pack_size


PATCH_TYPE_SEQUENTIAL  = 0
PATCH_TYPE_IN_PLACE    = 1
PATCH_TYPE_HDIFFPATCH  = 2

PATCH_TYPES = {
    'sequential': PATCH_TYPE_SEQUENTIAL,
    'in-place': PATCH_TYPE_IN_PLACE,
    'hdiffpatch': PATCH_TYPE_HDIFFPATCH
}

COMPRESSION_NONE        = 0
COMPRESSION_LZMA        = 1
COMPRESSION_CRLE        = 2
COMPRESSION_BZ2         = 3
COMPRESSION_HEATSHRINK  = 4
COMPRESSION_ZSTD        = 5
COMPRESSION_LZ4         = 6

COMPRESSIONS = {
    'none': COMPRESSION_NONE,
    'lzma': COMPRESSION_LZMA,
    'crle': COMPRESSION_CRLE,
    'bz2': COMPRESSION_BZ2,
    'heatshrink': COMPRESSION_HEATSHRINK,
    'zstd': COMPRESSION_ZSTD,
    'lz4': COMPRESSION_LZ4
}

HEADER_TYPE_USER = 1

DATA_FORMAT_ARM_CORTEX_M4 = 0
DATA_FORMAT_AARCH64       = 1
DATA_FORMAT_XTENSA_LX106  = 2

DATA_FORMATS = {
    'arm-cortex-m4': DATA_FORMAT_ARM_CORTEX_M4,
    'aarch64': DATA_FORMAT_AARCH64,
    'xtensa-lx106': DATA_FORMAT_XTENSA_LX106
}


def format_or(items):
    items = [str(item) for item in items]

    if len(items) == 1:
        return items[0]
    else:
        return '{} or {}'.format(', '.join(items[:-1]),
                                 items[-1])


def format_bad_compression_string(compression):
    return "Expected compression {}, but got {}.".format(
        format_or(sorted(COMPRESSIONS)),
        compression)


def format_bad_compression_number(compression):
    items = sorted([(n, '{}({})'.format(s, n)) for s, n in COMPRESSIONS.items()])

    return "Expected compression {}, but got {}.".format(
        format_or([v for _, v in items]),
        compression)


def format_bad_data_format(data_format):
    return 'Expected data format {}, but got {}.'.format(
        format_or(sorted(DATA_FORMATS)),
        data_format)


def format_bad_data_format_number(data_format):
    items = sorted([(n, '{}({})'.format(s, n)) for s, n in DATA_FORMATS.items()])

    return "Expected data format {}, but got {}.".format(
        format_or([v for _, v in items]),
        data_format)


def compression_string_to_number(compression):
    try:
        return COMPRESSIONS[compression]
    except KeyError:
        raise Error(format_bad_compression_string(compression))


def data_format_number_to_string(data_format):
    for string, number in DATA_FORMATS.items():
        if data_format == number:
            return string

    raise Error(format_bad_data_format_number(data_format))


def div_ceil(a, b):
    return (a + b - 1) // b


def file_size(f):
    position = f.tell()
    f.seek(0, os.SEEK_END)
    size = f.tell()
    f.seek(position, os.SEEK_SET)

    return size


def file_read(f):
    f.seek(0, os.SEEK_SET)

    return f.read()


def unpack_size_with_length(fin):
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


def unpack_size(fin):
    return unpack_size_with_length(fin)[0]


def unpack_size_bytes(data):
    return unpack_size(BytesIO(data))


def pack_usize(value):
    return pack_size(struct.unpack('>q', struct.pack('>Q', value))[0])


def unpack_usize(fin):
    return struct.unpack('>Q', struct.pack('>q', unpack_size(fin)))[0]


class DataSegment(object):

    def __init__(self,
                 from_data_offset_begin,
                 from_data_offset_end,
                 from_data_begin,
                 from_data_end,
                 from_code_begin,
                 from_code_end,
                 to_data_offset_begin,
                 to_data_offset_end,
                 to_data_begin,
                 to_data_end,
                 to_code_begin,
                 to_code_end):
        self.from_data_offset_begin = from_data_offset_begin
        self.from_data_offset_end = from_data_offset_end
        self.from_data_begin = from_data_begin
        self.from_data_end = from_data_end
        self.from_code_begin = from_code_begin
        self.from_code_end = from_code_end
        self.to_data_offset_begin = to_data_offset_begin
        self.to_data_offset_end = to_data_offset_end
        self.to_data_begin = to_data_begin
        self.to_data_end = to_data_end
        self.to_code_begin = to_code_begin
        self.to_code_end = to_code_end


def pack_header(patch_type, compression, fuser):
    if fuser is None:
        header = bitstruct.pack('p1u3u4', patch_type, compression)
    else:
        header = bitstruct.pack('b1u3u4', True, patch_type, compression)
        user = bitstruct.pack('u8', HEADER_TYPE_USER)
        user += pack_size(file_size(fuser))
        user += fuser.read()
        header += pack_size(len(user))
        header += user

    return header


def unpack_header(fpatch, fuser):
    header = fpatch.read(1)
    is_extended, patch_type, compression = bitstruct.unpack('b1u3u4', header)
    has_user = False

    if is_extended:
        extended_end = unpack_size(fpatch)
        extended_end += fpatch.tell()

        while fpatch.tell() < extended_end:
            header_type = fpatch.read(1)[0]
            size = unpack_size(fpatch)
            data = fpatch.read(size)

            if header_type == HEADER_TYPE_USER:
                has_user = True

                if fuser is not None:
                    fuser.write(data)

    return patch_type, compression, has_user


def peek_header_type(fpatch):
    position = fpatch.tell()
    header = fpatch.read(1)
    fpatch.seek(position, os.SEEK_SET)

    if len(header) != 1:
        raise Error('Failed to read the patch header.')

    return bitstruct.unpack('p1u3p4', header)[0]
