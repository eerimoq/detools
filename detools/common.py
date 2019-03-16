import os
from .errors import Error


PATCH_TYPE_NORMAL    = 0
PATCH_TYPE_IN_PLACE  = 1

COMPRESSIONS = {
    'none': 0,
    'lzma': 1,
    'crle': 2
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


def compression_string_to_number(compression):
    try:
        return COMPRESSIONS[compression]
    except KeyError:
        raise Error(format_bad_compression_string(compression))


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
