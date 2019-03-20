from io import StringIO
import difflib
from contextlib import redirect_stdout
from ..common import unpack_size

try:
    from .. import cbsdiff as bsdiff
except ImportError:
    from .. import bsdiff as bsdiff


class Blocks(object):

    def __init__(self):
        self._blocks = []

    def __len__(self):
        return len(self._blocks)

    def __iter__(self):
        for block in self._blocks:
            yield block

    def append(self, from_offset, to_address, values):
        self._blocks.append((from_offset, to_address, values))

    def to_bytes(self):
        data = [bsdiff.pack_size(len(self._blocks))]

        for from_offset, to_address, values in self._blocks:
            data.append(bsdiff.pack_size(from_offset))
            data.append(bsdiff.pack_size(to_address))
            data.append(bsdiff.pack_size(len(values)))
            data.extend([bsdiff.pack_size(value) for value in values])

        return b''.join(data)

    @classmethod
    def from_fpatch(cls, fpatch):
        blocks = cls()
        number_of_blocks = unpack_size(fpatch)[0]

        for _ in range(number_of_blocks):
            from_offset = unpack_size(fpatch)[0]
            to_address = unpack_size(fpatch)[0]
            number_of_values = unpack_size(fpatch)[0]
            values = [unpack_size(fpatch)[0] for _ in range(number_of_values)]
            blocks.append(from_offset, to_address, values)

        return blocks

    def __repr__(self):
        fout = StringIO()

        with redirect_stdout(fout):
            print('Blocks(', end='')
            print('number_of_blocks={}, '.format(len(self._blocks)), end='')
            print('blocks=[', end='')
            blocks = []

            for from_offset, to_address, values in self._blocks:
                blocks.append(
                    'Block(from_offset={}, to_address={}, '
                    'number_of_values={})'.format(
                        from_offset,
                        to_address,
                        len(values)))

            print(', '.join(blocks), end='')
            print('])')

        return fout.getvalue()


def get_matching_blocks(from_addresses, to_addresses):
    """Returns matching blocks.

    """

    from_offsets = []
    to_offsets = []

    for i in range(len(from_addresses) - 1):
        from_offsets.append(from_addresses[i + 1] - from_addresses[i])

    for i in range(len(to_addresses) - 1):
        to_offsets.append(to_addresses[i + 1] - to_addresses[i])

    sm = difflib.SequenceMatcher(None, from_offsets, to_offsets)
    matching_blocks = sm.get_matching_blocks()[:-1]

    return matching_blocks
