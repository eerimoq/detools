import os
import struct

from ._sais import sais


def _get_fsize(f):
    f.seek(0, os.SEEK_END)
    size = f.tell()
    f.seek(0, os.SEEK_SET)

    return size


def _pack_i64(value):
    return struct.pack('>q', value)


def _write_header(fpatch, new_size):
    fpatch.write(b'bsdiff01')
    fpatch.write(_pack_i64(new_size))


def create_patch(fold, fnew, fpatch):
    """This is likely a very slow operation. =/

    """

    _write_header(fpatch, _get_fsize(fnew))

    suffix_array = [_get_fsize(fold)]
    suffix_array += sais(fold.read())
