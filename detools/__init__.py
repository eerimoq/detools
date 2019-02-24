import sys
import argparse
from statistics import mean
from statistics import median
from humanfriendly import format_size

from .create import create_patch
from .apply import apply_patch
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


def _patch_info_normal(compression,
                       patch_size,
                       to_size,
                       diff_sizes,
                       extra_sizes,
                       _,
                       number_of_size_bytes):
    number_of_diff_bytes = sum(diff_sizes)
    number_of_extra_bytes = sum(extra_sizes)
    number_of_data_bytes = (number_of_diff_bytes + number_of_extra_bytes)
    size_data_ratio = round(100 * number_of_size_bytes / number_of_data_bytes, 1)
    patch_to_ratio = round(100 * patch_size / to_size, 1)

    if number_of_extra_bytes > 0:
        diff_extra_ratio = round(100 * number_of_diff_bytes / number_of_extra_bytes, 1)
    else:
        diff_extra_ratio = 'inf'

    print('Type:               normal')
    print('Patch size:         {}'.format(format_size(patch_size)))
    print('To size:            {}'.format(format_size(to_size)))
    print('Patch/to ratio:     {} % (lower is better)'.format(patch_to_ratio))
    print('Diff/extra ratio:   {} % (higher is better)'.format(diff_extra_ratio))
    print('Size/data ratio:    {} % (lower is better)'.format(size_data_ratio))
    print('Compression:        {}'.format(compression))
    print()
    print('Number of diffs:    {}'.format(len(diff_sizes)))
    print('Total diff size:    {}'.format(format_size(sum(diff_sizes))))
    print('Average diff size:  {}'.format(format_size(int(mean(diff_sizes)))))
    print('Median diff size:   {}'.format(format_size(int(median(diff_sizes)))))
    print()
    print('Number of extras:   {}'.format(len(extra_sizes)))
    print('Total extra size:   {}'.format(format_size(sum(extra_sizes))))
    print('Average extra size: {}'.format(format_size(int(mean(extra_sizes)))))
    print('Median extra size:  {}'.format(format_size(int(median(extra_sizes)))))


def _patch_info_in_place(number_of_segments, from_shift_size, info):
    print('Type:               in-place')
    print('Number of segments: {}'.format(number_of_segments))
    print('From shift size:    {}'.format(from_shift_size))
    print()

    for i, (from_offset, _, normal_info) in enumerate(info):
        print('-------------------- Patch {} --------------------'.format(i + 1))
        print()
        print('From offset:        {}'.format(format_size(from_offset)))
        _patch_info_normal(*normal_info)
        print()


def _do_patch_info(args):
    with open(args.patchfile, 'rb') as fpatch:
        patch_type, info = patch_info(fpatch)

        if patch_type == 'normal':
            _patch_info_normal(*info)
        elif patch_type == 'in-place':
            _patch_info_in_place(*info)
        else:
            raise Error('Bad patch type {}.'.format(patch_type))


def to_int(value):
    return int(value, 0)


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
                           type=to_int,
                           help='Target memory size.')
    subparser.add_argument(
        '--segment-size',
        type=to_int,
        help='Segment size. Must be a multiple of the largest erase block size.')
    subparser.add_argument(
        '--minimum-shift-size',
        type=to_int,
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

    # Patch info subparser.
    subparser = subparsers.add_parser('patch_info',
                                      description='Display patch info.')
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
