import lzma
from io import BytesIO
import bitstruct
from .errors import Error
from .compression.crle import CrleCompressor
from .compression.none import NoneCompressor
from .common import PATCH_TYPE_NORMAL
from .common import PATCH_TYPE_IN_PLACE
from .common import format_bad_compression_string
from .common import compression_string_to_number
from .common import div_ceil
from .common import file_size
from .common import file_read

try:
    from . import csais as sais
    from . import cbsdiff as bsdiff
except ImportError:
    print('detools: Failed to import C extensions. Using Python fallback.')
    from . import sais
    from . import bsdiff as bsdiff


def pack_header(patch_type, compression):
    return bitstruct.pack('p1u3u4', patch_type, compression)


def create_compressor(compression):
    if compression == 'lzma':
        compressor = lzma.LZMACompressor(format=lzma.FORMAT_ALONE)
    elif compression == 'none':
        compressor = NoneCompressor()
    elif compression == 'crle':
        compressor = CrleCompressor()
    else:
        raise Error(format_bad_compression_string(compression))

    return compressor


def create_patch_normal_data(ffrom, fto, fpatch, compression):
    to_size = file_size(fto)

    if to_size == 0:
        return

    from_data = file_read(ffrom)
    suffix_array = sais.sais(from_data)
    chunks = bsdiff.create_patch(suffix_array, from_data, file_read(fto))
    compressor = create_compressor(compression)

    for chunk in chunks:
        fpatch.write(compressor.compress(chunk))

    fpatch.write(compressor.flush())


def create_patch_normal(ffrom, fto, fpatch, compression):
    fpatch.write(pack_header(PATCH_TYPE_NORMAL,
                             compression_string_to_number(compression)))
    fpatch.write(bsdiff.pack_size(file_size(fto)))
    create_patch_normal_data(ffrom, fto, fpatch, compression)


def calc_shift(memory_size, segment_size, minimum_shift_size, from_size):
    """Shift from data as many segments as possible.

    """

    memory_segments = div_ceil(memory_size, segment_size)
    from_segments = div_ceil(from_size, segment_size)

    shift_segments = (memory_segments - from_segments)
    shift_size = (shift_segments * segment_size)

    if shift_size < minimum_shift_size:
        shift_size = minimum_shift_size

    return shift_size


def create_patch_in_place(ffrom,
                          fto,
                          fpatch,
                          compression,
                          memory_size,
                          segment_size,
                          minimum_shift_size):
    if (memory_size % segment_size) != 0:
        raise Error(
            'Memory size {} is not a multiple of segment size {}.'.format(
                memory_size,
                segment_size))

    if minimum_shift_size is None:
        minimum_shift_size = 2 * segment_size

    if (minimum_shift_size % segment_size) != 0:
        raise Error(
            'Minimum shift size {} is not a multiple of segment size {}.'.format(
                minimum_shift_size,
                segment_size))

    from_data = ffrom.read()
    from_size = len(from_data)
    to_data = fto.read()
    to_size = len(to_data)
    shift_size = calc_shift(memory_size,
                            segment_size,
                            minimum_shift_size,
                            len(from_data))
    shifted_size = (memory_size - shift_size)
    from_data = from_data[:shifted_size]
    number_of_to_segments = div_ceil(to_size, segment_size)

    # Create a normal patch for each segment.
    fsegments = BytesIO()

    for segment in range(number_of_to_segments):
        to_offset = (segment * segment_size)
        from_offset = max(to_offset + segment_size - shift_size, 0)
        fsegment = BytesIO()
        create_patch_normal_data(
            BytesIO(from_data[from_offset:]),
            BytesIO(to_data[to_offset:to_offset + segment_size]),
            fsegment,
            'none')
        fsegments.write(fsegment.getvalue())

    # Create the patch.
    fpatch.write(pack_header(PATCH_TYPE_IN_PLACE,
                             compression_string_to_number(compression)))
    fpatch.write(bsdiff.pack_size(memory_size))
    fpatch.write(bsdiff.pack_size(segment_size))
    fpatch.write(bsdiff.pack_size(shift_size))
    fpatch.write(bsdiff.pack_size(from_size))
    fpatch.write(bsdiff.pack_size(to_size))

    if to_size == 0:
        return

    compressor = create_compressor(compression)
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
    """Create a patch from `ffrom` to `fto` and write it to `fpatch`. All
    three arguments are file-like objects.

    `compression` must be ``'crle'``, ``'lzma'`` or ``'none'``.

    `patch_type` must be ``'normal'`` or ``'in-place'``.

    `memory_size`, `segment_size` and `minimum_shift_size` are used
    when creating an in-place patch.

    >>> ffrom = open('foo.old', 'rb')
    >>> fto = open('foo.new', 'rb')
    >>> fpatch = open('foo.patch', 'wb')
    >>> create_patch(ffrom, fto, fpatch)

    """

    if patch_type == 'normal':
        create_patch_normal(ffrom, fto, fpatch, compression)
    elif patch_type == 'in-place':
        create_patch_in_place(ffrom,
                              fto,
                              fpatch,
                              compression,
                              memory_size,
                              segment_size,
                              minimum_shift_size)
    else:
        raise Error("Bad patch type '{}'.".format(patch_type))


def create_patch_filenames(fromfile,
                           tofile,
                           patchfile,
                           compression='lzma',
                           patch_type='normal',
                           memory_size=None,
                           segment_size=None,
                           minimum_shift_size=None):
    """Same as :func:`~detools.create_patch()`, but with filenames instead
    of file-like objects.

    >>> create_patch_filenames('foo.old', 'foo.new', 'foo.patch')

    """

    with open(fromfile, 'rb') as ffrom:
        with open(tofile, 'rb') as fto:
            with open(patchfile, 'wb') as fpatch:
                create_patch(ffrom,
                             fto,
                             fpatch,
                             compression,
                             patch_type,
                             memory_size,
                             segment_size,
                             minimum_shift_size)
