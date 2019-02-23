import os
import struct
from lzma import LZMACompressor

try:
    from . import csais as sais
    from . import cbsdiff as bsdiff
except ImportError:
    print('detools: Failed to import C extensions. Using Python fallback.')
    from . import sais
    from . import bsdiff as bsdiff


COMPRESSIONS = {
    'lzma': b'lzma',
    'none': b'none'
}


class NoneCompressor(object):

    def compress(self, data):
        return data

    def flush(self):
        return b''


def _get_fsize(f):
    f.seek(0, os.SEEK_END)

    return f.tell()


def fread(f):
    f.seek(0, os.SEEK_SET)

    return f.read()


def _write_header(fpatch, fto, compression):
    fpatch.write(b'detools')
    fpatch.write(b'0')
    fpatch.write(COMPRESSIONS[compression])
    fpatch.write(struct.pack('>q', _get_fsize(fto)))


def _write_data(ffrom, fto, fpatch, compression):
    from_data = fread(ffrom)
    suffix_array = sais.sais(from_data)
    chunks = bsdiff.create_patch(suffix_array, from_data, fread(fto))

    if compression == 'lzma':
        compressor = LZMACompressor()
    elif compression == 'none':
        compressor = NoneCompressor()
    else:
        raise ValueError(
            'Expected compression lzma or none, but got {}.'.format(
                compression))

    for chunk in chunks:
        fpatch.write(compressor.compress(chunk))

    fpatch.write(compressor.flush())


def create_patch(ffrom, fto, fpatch, compression='lzma'):
    """Create a patch from `ffrom` to `fto` and write it to `fpatch`.

    """

    _write_header(fpatch, fto, compression)
    _write_data(ffrom, fto, fpatch, compression)
