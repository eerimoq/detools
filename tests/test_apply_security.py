import unittest
from io import BytesIO

import detools
from detools.common import pack_size
from detools.create import pack_header


def make_sequential_patch(*chunks):
    patch = bytearray()
    patch += pack_header(0, 0)
    patch += pack_size(1)

    for chunk in chunks:
        patch += chunk

    return bytes(patch)


def make_in_place_patch(memory_size,
                        segment_size,
                        shift_size,
                        from_size,
                        to_size,
                        *chunks):
    patch = bytearray()
    patch += pack_header(1, 0)
    patch += pack_size(memory_size)
    patch += pack_size(segment_size)
    patch += pack_size(shift_size)
    patch += pack_size(from_size)
    patch += pack_size(to_size)

    for chunk in chunks:
        patch += chunk

    return bytes(patch)


class RecordingBytesIO(BytesIO):

    def __init__(self, data):
        super().__init__(data)
        self.read_args = []

    def read(self, size=-1):
        self.read_args.append(size)

        return super().read(size)


class ApplySecurityTest(unittest.TestCase):

    def test_apply_patch_rejects_negative_diff_size(self):
        patch = make_sequential_patch(
            pack_size(0),
            pack_size(-1),
            pack_size(1),
            b'A',
            pack_size(0))

        with self.assertRaisesRegex(detools.Error, 'Patch diff data too long'):
            detools.apply_patch(BytesIO(b''), BytesIO(patch), BytesIO())

    def test_apply_patch_rejects_negative_extra_size(self):
        patch = make_sequential_patch(
            pack_size(0),
            pack_size(1),
            b'\x01',
            pack_size(-1),
            pack_size(0))

        with self.assertRaisesRegex(detools.Error, 'Patch extra data too long'):
            detools.apply_patch(BytesIO(b'@'), BytesIO(patch), BytesIO())

    def test_apply_patch_rejects_negative_dfpatch_size(self):
        patch = make_sequential_patch(pack_size(-1))

        with self.assertRaisesRegex(detools.Error,
                                    'Expected data format patch size >= 0'):
            detools.apply_patch(BytesIO(b''), BytesIO(patch), BytesIO())

    def test_apply_patch_in_place_rejects_negative_from_size_before_read(self):
        patch = make_in_place_patch(
            1,
            1,
            0,
            -1,
            1,
            pack_size(0),
            pack_size(0),
            pack_size(1),
            b'A',
            pack_size(0))
        memory = RecordingBytesIO(b'Z')

        with self.assertRaisesRegex(detools.Error, 'Expected from size >= 0'):
            detools.apply_patch_in_place(memory, BytesIO(patch))

        self.assertEqual(memory.read_args, [])

    def test_apply_patch_in_place_rejects_zero_segment_size(self):
        patch = make_in_place_patch(1, 0, 0, 1, 1)

        with self.assertRaisesRegex(detools.Error, 'Expected segment size > 0'):
            detools.apply_patch_in_place(BytesIO(b'Z'), BytesIO(patch))

    def test_apply_patch_in_place_rejects_shift_larger_than_memory(self):
        patch = make_in_place_patch(1, 1, 2, 1, 1)

        with self.assertRaisesRegex(detools.Error, 'Expected shift size <= memory size'):
            detools.apply_patch_in_place(BytesIO(b'Z'), BytesIO(patch))

    def test_apply_patch_in_place_rejects_short_source_reads(self):
        patch = make_in_place_patch(
            1,
            1,
            1,
            1,
            1,
            pack_size(0),
            pack_size(1),
            b'\x00',
            pack_size(0),
            pack_size(0))

        with self.assertRaisesRegex(detools.Error,
                                    'Patch diff data exceeds available source data'):
            detools.apply_patch_in_place(BytesIO(b'Z'), BytesIO(patch))

    def test_apply_patch_rejects_invalid_heatshrink_header(self):
        patch = bytearray()
        patch += pack_header(0, 4)
        patch += pack_size(1)
        patch += b'\xff'

        with self.assertRaisesRegex(detools.Error, 'Patch decompression failed'):
            detools.apply_patch(BytesIO(b''), BytesIO(patch), BytesIO())
