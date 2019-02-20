import sys
import argparse
from .create_patch import create_patch
from .apply_patch import apply_patch
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


def _main():
    parser = argparse.ArgumentParser(description='Binary diff/patch utility.')

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

    args = parser.parse_args()

    if args.debug:
        args.func(args)
    else:
        try:
            args.func(args)
        except BaseException as e:
            sys.exit('error: ' + str(e))
