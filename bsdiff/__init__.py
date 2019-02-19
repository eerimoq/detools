import sys
import argparse
from .bsdiff import create_patch
from .bsdiff import apply_patch
from .errors import Error
from .version import __version__


def _do_create_patch(args):
    with open(args.oldfile, 'rb') as fold:
        with open(args.newfile, 'rb') as fnew:
            with open(args.patchfile, 'wb') as fpatch:
                create_patch(fold, fnew, fpatch)


def _do_apply_patch(args):
    with open(args.oldfile, 'rb') as fold:
        with open(args.newfile, 'wb') as fnew:
            with open(args.patchfile, 'rb') as fpatch:
                apply_patch(fold, fpatch, fnew)


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
    subparser.add_argument('oldfile', help='Old file.')
    subparser.add_argument('newfile', help='New file.')
    subparser.add_argument('patchfile', help='Created patch file.')
    subparser.set_defaults(func=_do_create_patch)

    # Apply patch subparser.
    subparser = subparsers.add_parser('apply_patch',
                                      description='Apply given patch.')
    subparser.add_argument('oldfile', help='Old file.')
    subparser.add_argument('patchfile', help='Patch file.')
    subparser.add_argument('newfile', help='Created new file.')
    subparser.set_defaults(func=_do_apply_patch)

    args = parser.parse_args()

    if args.debug:
        args.func(args)
    else:
        try:
            args.func(args)
        except BaseException as e:
            sys.exit('error: ' + str(e))
