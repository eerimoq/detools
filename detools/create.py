import os
import lzma
from io import BytesIO
import bitstruct
from .errors import Error
from .crle import CrleCompressor
from .none import NoneCompressor
from .common import PATCH_TYPE_NORMAL
from .common import PATCH_TYPE_IN_PLACE
from .common import COMPRESSIONS

try:
    from . import csais as sais
    from . import cbsdiff as bsdiff
except ImportError:
    print('detools: Failed to import C extensions. Using Python fallback.')
    from . import sais
    from . import bsdiff as bsdiff


def get_fsize(f):
    f.seek(0, os.SEEK_END)

    return f.tell()


def pack_header(patch_type, compression):
    return bitstruct.pack('p1u3u4', patch_type, compression)


def fread(f):
    f.seek(0, os.SEEK_SET)

    return f.read()


def _create_compressor(compression):
    if compression == 'lzma':
        compressor = lzma.LZMACompressor(format=lzma.FORMAT_ALONE)
    elif compression == 'none':
        compressor = NoneCompressor()
    elif compression == 'crle':
        compressor = CrleCompressor()
    else:
        raise Error(
            'Expected compression lzma or none, but got {}.'.format(
                compression))

    return compressor


def _create_patch_normal(ffrom, fto, fpatch, compression):
    # Header.
    fpatch.write(pack_header(PATCH_TYPE_NORMAL, COMPRESSIONS[compression]))
    fpatch.write(bsdiff.pack_size(get_fsize(fto)))

    # Data.
    from_data = fread(ffrom)
    suffix_array = sais.sais(from_data)
    chunks = bsdiff.create_patch(suffix_array, from_data, fread(fto))
    compressor = _create_compressor(compression)

    for chunk in chunks:
        fpatch.write(compressor.compress(chunk))

    fpatch.write(compressor.flush())


def _div_ceil(a, b):
    return (a + b - 1) // b


def _calc_shift(memory_size, segment_size, minimum_shift_size, from_size):
    """Shift from data as many segments as possible.

    """

    memory_segments = _div_ceil(memory_size, segment_size)
    from_segments = _div_ceil(from_size, segment_size)

    shift_segments = (memory_segments - from_segments)
    shift_size = (shift_segments * segment_size)

    if shift_size < minimum_shift_size:
        shift_size = minimum_shift_size

    return shift_size


def _create_patch_in_place(ffrom,
                           fto,
                           fpatch,
                           compression,
                           memory_size,
                           segment_size,
                           minimum_shift_size):
    if (memory_size % segment_size) != 0:
        raise Error('Memory size must be a multiple of segment size.')

    if minimum_shift_size is None:
        minimum_shift_size = 2 * segment_size

    if (minimum_shift_size % segment_size) != 0:
        raise Error('Minimum shift size must be a multiple of segment size.')

    from_data = ffrom.read()
    to_data = fto.read()
    shift_size = _calc_shift(memory_size,
                             segment_size,
                             minimum_shift_size,
                             len(from_data))
    shifted_size = (memory_size - shift_size)
    from_data = from_data[:shifted_size]
    number_of_to_segments = _div_ceil(len(to_data), segment_size)

    # Create a normal patch for each segment.
    fsegments = BytesIO()

    for segment in range(number_of_to_segments):
        to_offset = (segment * segment_size)
        from_offset = max(to_offset + segment_size - shift_size, 0)
        fsegment = BytesIO()
        _create_patch_normal(BytesIO(from_data[from_offset:]),
                             BytesIO(to_data[to_offset:to_offset + segment_size]),
                             fsegment,
                             'none')
        segment_data = fsegment.getvalue()
        fsegments.write(bsdiff.pack_size(from_offset))
        fsegments.write(segment_data)

    # Create the patch.
    fpatch.write(pack_header(PATCH_TYPE_IN_PLACE, COMPRESSIONS[compression]))
    fpatch.write(bsdiff.pack_size(len(to_data)))
    fpatch.write(bsdiff.pack_size(shift_size))
    compressor = _create_compressor(compression)
    fpatch.write(compressor.compress(fsegments.getvalue()))
    fpatch.write(compressor.flush())


def create_patch(ffrom,
                 fto,
                 fpatch,
                 compression='lzma',
                 patch_type='normal',
                 memory_size=None,
                 segment_size=None,
                 minimum_shift_size=None):
    """Create a patch from `ffrom` to `fto` and write it to `fpatch`.

    """

    if patch_type == 'normal':
        _create_patch_normal(ffrom, fto, fpatch, compression)
    elif patch_type == 'in-place':
        _create_patch_in_place(ffrom,
                               fto,
                               fpatch,
                               compression,
                               memory_size,
                               segment_size,
                               minimum_shift_size)
    else:
        raise Error("Bad patch type '{}'.".format(patch_type))
