import sys
import argparse
from statistics import mean
from statistics import median
from humanfriendly import format_size
from humanfriendly import parse_size

from .create import create_patch
from .apply import apply_patch
from .apply import apply_patch_in_place
from .info import patch_info
from .errors import Error
from .version import __version__


def _do_create_patch(args):
    if args.type == 'in-place':
        if args.memory_size is None:
            raise Error('--memory-size is required for in-place patch.')

        if args.segment_size is None:
            raise Error('--segment-size is required for in-place patch.')

    with open(args.fromfile, 'rb') as ffrom:
        with open(args.tofile, 'rb') as fto:
            with open(args.patchfile, 'wb') as fpatch:
                create_patch(ffrom,
                             fto,
                             fpatch,
                             args.compression,
                             patch_type=args.type,
                             memory_size=args.memory_size,
                             segment_size=args.segment_size,
                             minimum_shift_size=args.minimum_shift_size)


def _do_apply_patch(args):
    with open(args.fromfile, 'rb') as ffrom:
        with open(args.patchfile, 'rb') as fpatch:
            with open(args.tofile, 'wb') as fto:
                apply_patch(ffrom, fpatch, fto)


def _do_apply_patch_in_place(args):
    with open(args.memfile, 'r+b') as fmem:
        with open(args.patchfile, 'rb') as fpatch:
            apply_patch_in_place(fmem, fpatch)


def _format_size(value):
    return format_size(value, binary=True)


def _format_bytes(value):
    return '{} bytes'.format(value)


def _format_ratio(numerator, denominator):
    if denominator > 0:
        return round(100 * numerator / denominator, 1)
    else:
        return 'inf'


def _patch_info_in_place_segment(fsize,
                                 segment_index,
                                 from_offset_begin,
                                 from_offset_end,
                                 to_offset_begin,
                                 to_offset_end,
                                 to_size,
                                 diff_sizes,
                                 extra_sizes,
                                 adjustment_sizes,
                                 number_of_size_bytes):
    del to_size
    del adjustment_sizes

    number_of_diff_bytes = sum(diff_sizes)
    number_of_extra_bytes = sum(extra_sizes)
    number_of_data_bytes = (number_of_diff_bytes + number_of_extra_bytes)
    size_data_ratio = _format_ratio(number_of_size_bytes, number_of_data_bytes)
    diff_extra_ratio = _format_ratio(number_of_diff_bytes, number_of_extra_bytes)

    print('------------------- Segment {} -------------------'.format(
        segment_index))
    print()
    print('From range:         {} - {}'.format(fsize(from_offset_begin),
                                               fsize(from_offset_end)))
    print('To range:           {} - {}'.format(fsize(to_offset_begin),
                                               fsize(to_offset_end)))
    print('Diff/extra ratio:   {} % (higher is better)'.format(diff_extra_ratio))
    print('Size/data ratio:    {} % (lower is better)'.format(size_data_ratio))
    print()
    print('Number of diffs:    {}'.format(len(diff_sizes)))
    print('Total diff size:    {}'.format(fsize(sum(diff_sizes))))
    print('Average diff size:  {}'.format(fsize(int(mean(diff_sizes)))))
    print('Median diff size:   {}'.format(fsize(int(median(diff_sizes)))))
    print()
    print('Number of extras:   {}'.format(len(extra_sizes)))
    print('Total extra size:   {}'.format(fsize(sum(extra_sizes))))
    print('Average extra size: {}'.format(fsize(int(mean(extra_sizes)))))
    print('Median extra size:  {}'.format(fsize(int(median(extra_sizes)))))
    print()


def _patch_info_normal(fsize,
                       patch_size,
                       compression,
                       to_size,
                       diff_sizes,
                       extra_sizes,
                       adjustment_sizes,
                       number_of_size_bytes):
    del adjustment_sizes

    number_of_diff_bytes = sum(diff_sizes)
    number_of_extra_bytes = sum(extra_sizes)
    number_of_data_bytes = (number_of_diff_bytes + number_of_extra_bytes)
    size_data_ratio = _format_ratio(number_of_size_bytes, number_of_data_bytes)
    patch_to_ratio = _format_ratio(patch_size, to_size)
    diff_extra_ratio = _format_ratio(number_of_diff_bytes, number_of_extra_bytes)

    if diff_sizes:
        mean_diff_size = fsize(int(mean(diff_sizes)))
        median_diff_size = fsize(int(median(diff_sizes)))
    else:
        mean_diff_size = '-'
        median_diff_size = '-'

    if extra_sizes:
        mean_extra_size = fsize(int(mean(extra_sizes)))
        median_extra_size = fsize(int(median(extra_sizes)))
    else:
        mean_extra_size = '-'
        median_extra_size = '-'

    print('Type:               normal')
    print('Patch size:         {}'.format(fsize(patch_size)))
    print('To size:            {}'.format(fsize(to_size)))
    print('Patch/to ratio:     {} % (lower is better)'.format(patch_to_ratio))
    print('Diff/extra ratio:   {} % (higher is better)'.format(diff_extra_ratio))
    print('Size/data ratio:    {} % (lower is better)'.format(size_data_ratio))
    print('Compression:        {}'.format(compression))
    print()
    print('Number of diffs:    {}'.format(len(diff_sizes)))
    print('Total diff size:    {}'.format(fsize(sum(diff_sizes))))
    print('Average diff size:  {}'.format(mean_diff_size))
    print('Median diff size:   {}'.format(median_diff_size))
    print()
    print('Number of extras:   {}'.format(len(extra_sizes)))
    print('Total extra size:   {}'.format(fsize(sum(extra_sizes))))
    print('Average extra size: {}'.format(mean_extra_size))
    print('Median extra size:  {}'.format(median_extra_size))


def _patch_info_in_place(fsize,
                         patch_size,
                         compression,
                         memory_size,
                         segment_size,
                         from_shift_size,
                         from_size,
                         to_size,
                         segments):
    patch_to_ratio = _format_ratio(patch_size, to_size)

    print('Type:               in-place')
    print('Patch size:         {}'.format(fsize(patch_size)))
    print('Memory size:        {}'.format(fsize(memory_size)))
    print('Segment size:       {}'.format(fsize(segment_size)))
    print('From shift size:    {}'.format(fsize(from_shift_size)))
    print('From size:          {}'.format(fsize(from_size)))
    print('To size:            {}'.format(fsize(to_size)))
    print('Patch/to ratio:     {} % (lower is better)'.format(patch_to_ratio))
    print('Number of segments: {}'.format(len(segments)))
    print('Compression:        {}'.format(compression))
    print()

    for i, normal_info in enumerate(segments):
        from_offset_begin = max(segment_size * (i + 1) - from_shift_size, 0)
        from_offset_end = min(from_size, memory_size - from_shift_size)
        to_offset_begin = (segment_size * i)
        to_offset_end = min(to_offset_begin + segment_size, to_size)
        _patch_info_in_place_segment(fsize,
                                     i + 1,
                                     from_offset_begin,
                                     from_offset_end,
                                     to_offset_begin,
                                     to_offset_end,
                                     *normal_info)


def _do_patch_info(args):
    with open(args.patchfile, 'rb') as fpatch:
        patch_type, info = patch_info(fpatch)

    if args.no_human:
        fsize = _format_bytes
    else:
        fsize = _format_size

    if patch_type == 'normal':
        _patch_info_normal(fsize, *info)
    elif patch_type == 'in-place':
        _patch_info_in_place(fsize, *info)
    else:
        raise Error('Bad patch type {}.'.format(patch_type))


def to_binary_size(value):
    return parse_size(value, binary=True)


def _main():
    parser = argparse.ArgumentParser(description='Binary delta encoding utility.')

    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('--version',
                        action='version',
                        version=__version__,
                        help='Print version information and exit.')

    # Workaround to make the subparser required in Python 3.
    subparsers = parser.add_subparsers(title='subcommands',
                                       dest='subcommand')
    subparsers.required = True

    # Create patch subparser.
    subparser = subparsers.add_parser('create_patch',
                                      description='Create a patch.')
    subparser.add_argument('-t', '--type',
                           choices=('normal', 'in-place'),
                           default='normal',
                           help='Patch type (default: normal).')
    subparser.add_argument('-c', '--compression',
                           choices=('lzma', 'crle', 'none'),
                           default='lzma',
                           help='Compression algorithm (default: lzma).')
    subparser.add_argument('--memory-size',
                           type=to_binary_size,
                           help='Target memory size.')
    subparser.add_argument(
        '--segment-size',
        type=to_binary_size,
        help='Segment size. Must be a multiple of the largest erase block size.')
    subparser.add_argument(
        '--minimum-shift-size',
        type=to_binary_size,
        help='Minimum shift size (default: 2 * segment size).')
    subparser.add_argument('fromfile', help='From file.')
    subparser.add_argument('tofile', help='To file.')
    subparser.add_argument('patchfile', help='Created patch file.')
    subparser.set_defaults(func=_do_create_patch)

    # Apply patch subparser.
    subparser = subparsers.add_parser('apply_patch',
                                      description='Apply given patch.')
    subparser.add_argument('fromfile', help='From file.')
    subparser.add_argument('patchfile', help='Patch file.')
    subparser.add_argument('tofile', help='Created to file.')
    subparser.set_defaults(func=_do_apply_patch)

    # In-place apply patch subparser.
    subparser = subparsers.add_parser('apply_patch_in_place',
                                      description='Apply given in-place patch.')
    subparser.add_argument('memfile', help='Memory file.')
    subparser.add_argument('patchfile', help='Patch file.')
    subparser.set_defaults(func=_do_apply_patch_in_place)

    # Patch info subparser.
    subparser = subparsers.add_parser('patch_info',
                                      description='Display patch info.')
    subparser.add_argument('--no-human',
                           action='store_true',
                           help='Print sizes without units.')
    subparser.add_argument('patchfile', help='Patch file.')
    subparser.set_defaults(func=_do_patch_info)

    args = parser.parse_args()

    if args.debug:
        args.func(args)
    else:
        try:
            args.func(args)
        except BaseException as e:
            sys.exit('error: ' + str(e))
