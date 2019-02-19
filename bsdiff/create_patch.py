import os
import struct


def _pack_i64(value):
    return struct.pack('>q', value)


def _write_header(fpatch, fnew):
    # Magic.
    fpatch.write(b'bsdiff01')

    # New size.
    fnew.seek(0, os.SEEK_END)
    new_size = fnew.tell()
    fnew.seek(0, os.SEEK_SET)

    fpatch.write(_pack_i64(new_size))


def create_patch(fold, fnew, fpatch):
    """This is likely a very slow operation. =/

    """

    _write_header(fpatch, fnew)
