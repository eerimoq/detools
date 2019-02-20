import os
import struct
from lzma import LZMACompressor

from . import _sais
from . import _bsdiff


def _get_fsize(f):
    f.seek(0, os.SEEK_END)

    return f.tell()


def fread(f):
    f.seek(0, os.SEEK_SET)

    return f.read()


def _pack_i64(value):
    return struct.pack('>q', value)


def _write_header(fpatch, fnew):
    fpatch.write(b'bsdiff01')
    fpatch.write(_pack_i64(_get_fsize(fnew)))


def _write_data(fold, fnew, fpatch):
    old = fread(fold)
    suffix_array = [_get_fsize(fold)]
    suffix_array += _sais.sais(old)
    chunks = _bsdiff.create_patch(suffix_array, old, fread(fnew))
    compressor = LZMACompressor()

    for chunk in chunks:
        fpatch.write(compressor.compress(chunk))

    fpatch.write(compressor.flush())


def create_patch(fold, fnew, fpatch):
    """Create a patch from `fold` to `fnew` and write it to `fpatch`.

    """

    _write_header(fpatch, fnew)
    _write_data(fold, fnew, fpatch)
