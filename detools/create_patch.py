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


def _write_header(fpatch, fto):
    fpatch.write(b'detools0')
    fpatch.write(_pack_i64(_get_fsize(fto)))


def _write_data(ffrom, fto, fpatch):
    from_data = fread(ffrom)
    suffix_array = [_get_fsize(ffrom)]
    suffix_array += _sais.sais(from_data)
    chunks = _bsdiff.create_patch(suffix_array, from_data, fread(fto))
    compressor = LZMACompressor()

    for chunk in chunks:
        fpatch.write(compressor.compress(chunk))

    fpatch.write(compressor.flush())


def create_patch(ffrom, fto, fpatch):
    """Create a patch from `ffrom` to `fto` and write it to `fpatch`.

    """

    _write_header(fpatch, fto)
    _write_data(ffrom, fto, fpatch)
