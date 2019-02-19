import sys
import argparse
from .bsdiff import patch
from .version import __version__


def _do_patch(args):
    with open(args.oldfile, 'rb') as fold:
        with open(args.newfile, 'wb') as fnew:
            with open(args.patchfile, 'rb') as fpatch:
                patch(fold, fpatch, fnew)


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

    patch_parser = subparsers.add_parser('patch',
                                         description='Apply given patch.')
    parser.add_argument('oldfile', help='Old file.')
    parser.add_argument('patchfile', help='Patch file.')
    parser.add_argument('newfile', help='New file.')
    patch_parser.set_defaults(func=_do_patch)

    args = parser.parse_args()

    if args.debug:
        args.func(args)
    else:
        try:
            args.func(args)
        except BaseException as e:
            sys.exit('error: ' + str(e))
