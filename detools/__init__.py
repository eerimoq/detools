import sys
import argparse
from statistics import mean
from statistics import median
from humanfriendly import format_size

from .create_patch import create_patch
from .apply_patch import apply_patch
from .apply_patch import patch_info
from .errors import Error
from .version import __version__


def _do_create_patch(args):
    with open(args.fromfile, 'rb') as ffrom:
        with open(args.tofile, 'rb') as fto:
            with open(args.patchfile, 'wb') as fpatch:
                create_patch(ffrom, fto, fpatch)


def _do_apply_patch(args):
    with open(args.fromfile, 'rb') as ffrom:
        with open(args.patchfile, 'rb') as fpatch:
            with open(args.tofile, 'wb') as fto:
                apply_patch(ffrom, fpatch, fto)


def _do_patch_info(args):
    with open(args.patchfile, 'rb') as fpatch:
        (patch_size,
         to_size,
         diff_sizes,
         extra_sizes,
         adjustment_sizes) = patch_info(fpatch)

    number_of_size_bytes = 8 * len(diff_sizes + extra_sizes + adjustment_sizes)
    number_of_data_bytes = sum(diff_sizes + extra_sizes)
    size_data_ratio = int(100 * number_of_size_bytes / number_of_data_bytes)
    patch_to_ratio = int(100 * patch_size / to_size)

    print('Patch size:         {}'.format(format_size(patch_size)))
    print('To size:            {}'.format(format_size(to_size)))
    print('Patch/to ratio:     {} % (lower is better)'.format(patch_to_ratio))
    print('Size/data ratio:    {} % (lower is better)'.format(size_data_ratio))
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
