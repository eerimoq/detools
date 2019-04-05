from io import StringIO
import difflib
import textwrap
from contextlib import redirect_stdout
from ..common import pack_size
from ..common import unpack_size


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
        data = [pack_size(len(self._blocks))]

        for from_offset, to_address, values in self._blocks:
            data.append(pack_size(from_offset))
            data.append(pack_size(to_address))
            data.append(pack_size(len(values)))
            data.extend([pack_size(value) for value in values])

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
            blocks = []

            for from_offset, to_address, values in self._blocks:
                blocks.append(
                    'Block(from_offset={}, to_address={}, '
                    'number_of_values={})'.format(
                        from_offset,
                        to_address,
                        len(values)))

            print(
                'Blocks(number_of_blocks={}, blocks=[{}])'.format(
                    len(self._blocks),
                    ', '.join(blocks)),
                end='')

        return fout.getvalue()


def get_matching_blocks(from_addresses, to_addresses):
    """Returns matching blocks based on address differences.

    """

    from_offsets = []
    to_offsets = []

    for i in range(len(from_addresses) - 1):
        from_offsets.append(from_addresses[i + 1] - from_addresses[i])

    for i in range(len(to_addresses) - 1):
        to_offsets.append(to_addresses[i + 1] - to_addresses[i])

    sm = difflib.SequenceMatcher(None, from_offsets, to_offsets)

    return sm.get_matching_blocks()[:-1]


def create_patch_block_4_bytes(ffrom, fto, from_dict, to_dict):
    """Returns a bytes object of blocks.

    """

    blocks = Blocks()

    if not from_dict or not to_dict:
        return blocks.to_bytes()

    from_sorted = sorted(from_dict.items())
    to_sorted = sorted(to_dict.items())
    from_addresses, from_values = zip(*from_sorted)
    to_addresses, to_values = zip(*to_sorted)
    matching_blocks = get_matching_blocks(from_addresses, to_addresses)

    for from_offset, to_offset, size in matching_blocks:
        # Skip small blocks as the block overhead is too big.
        if size < 8:
            continue

        size += 1
        from_slice = from_values[from_offset:from_offset + size]
        to_slice = to_values[to_offset:to_offset + size]
        blocks.append(from_offset,
                      to_addresses[to_offset],
                      [fv - tv for fv, tv in zip(from_slice, to_slice)])

        # Overwrite blocks with zeros.
        for address in from_addresses[from_offset:from_offset + size]:
            ffrom.seek(address)
            ffrom.write(4 * b'\x00')

        for address in to_addresses[to_offset:to_offset + size]:
            fto.seek(address)
            fto.write(4 * b'\x00')

    return blocks.to_bytes()


def write_zeros_to_from_4_bytes(ffrom, blocks, from_dict):
    from_sorted = sorted(from_dict.items())

    for from_offset, _, values in blocks:
        for i in range(len(values)):
            from_address = from_sorted[from_offset + i][0]
            ffrom.seek(from_address)
            ffrom.write(4 * b'\x00')


def load_blocks(fpatch):
    position = fpatch.tell()
    blocks = Blocks.from_fpatch(fpatch)
    blocks_size = fpatch.tell() - position

    return blocks, blocks_size


def format_blocks(blocks, blocks_size, fsize):
    print('Number of blocks:   {}'.format(len(blocks)))
    print('Size:               {}'.format(fsize(blocks_size)))
    print()

    for i, (from_offset, to_address, values) in enumerate(blocks):
        print('------------------- Block {} -------------------'.format(i + 1))
        print()
        print('From offset:        {}'.format(from_offset))
        print('To address:         0x{:x}'.format(to_address))
        print('Number of values:   {}'.format(len(values)))
        print('Values:')
        lines = textwrap.wrap(' '.join([str(value) for value in values]))
        lines = ['  ' + line for line in lines]
        print('\n'.join(lines))
        print()
