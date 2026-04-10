import unittest
import struct
import mmap
import tempfile
from contextlib import contextmanager

import detools.bsdiff


def read_file(filename):
    with open(filename, 'rb') as fin:
        return fin.read()


def suffix_array_list_to_bytearray(suffix_array):
    return bytearray().join([
        struct.pack('=i', value) for value in suffix_array
    ])


@contextmanager
def sparse_mmap(size, access):
    with tempfile.TemporaryFile() as file_p:
        file_p.truncate(size)
        map_p = mmap.mmap(file_p.fileno(), size, access=access)

        try:
            yield map_p
        finally:
            map_p.close()


class DetoolsBsdiffTest(unittest.TestCase):

    def test_bsdiff(self):
        datas = [
            (
                [0],
                b'',
                b'',
                []
            ),
            (
                [1, 0],
                b'1',
                b'12',
                [
                    b'\x01', b'\x00', b'\x01', b'2', b'\x41'
                ]
            ),
            (
                [4, 0, 1, 2, 3],
                b'1234',
                b'29990812398409812',
                [
                    b'\x00', b'', b'\x11', b'29990812398409812', b'\x01'
                ]
            ),
            (
                [
                    41, 28, 32, 29, 34, 31, 37, 33, 38, 35,
                    30, 36,  5,  4,  0, 10,  1, 13, 23, 12,
                    39, 25, 40, 17, 27,  3, 16,  6,  7,  8,
                    26,  9, 11, 14, 15,  2, 22, 21, 20, 19,
                    18, 24
                ],
                b'adska9kkkoaofeopkjvuuuuewflk-0920314923fg',
                b'adska9kkkoaofeopkjvuuuuewflk-0920314923fg1',
                [
                    b'\x29',
                    b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                    b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                    b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                    b'\x01',
                    b'1',
                    b'\x47'
                ]
            )
        ]

        for suffix_array, from_data, to_data, chunks in datas:
            suffix_array = suffix_array_list_to_bytearray(suffix_array)
            self.assertEqual(
                detools.bsdiff.create_patch(suffix_array,
                                            from_data,
                                            to_data,
                                            bytearray(4 * (len(from_data) + 1))),
                chunks)

    def test_bsdiff_rejects_too_small_diff_buffer(self):
        suffix_array = suffix_array_list_to_bytearray([1, 0])

        with self.assertRaisesRegex(ValueError, 'Diff buffer is too small'):
            detools.bsdiff.create_patch(suffix_array, b'A', b'BC', bytearray(1))

    def test_bsdiff_rejects_invalid_suffix_array_entries(self):
        suffix_array = suffix_array_list_to_bytearray([1, 999])

        with self.assertRaisesRegex(ValueError, 'Suffix array entry 1 is out of range'):
            detools.bsdiff.create_patch(suffix_array, b'A', b'B', bytearray(2))

    def test_bsdiff_rejects_input_larger_than_int32(self):
        huge_size = 2 ** 31
        suffix_array_size = 4 * (huge_size + 1)

        with sparse_mmap(huge_size, mmap.ACCESS_READ) as from_mmap:
            with sparse_mmap(suffix_array_size, mmap.ACCESS_WRITE) as suffix_array:
                with self.assertRaisesRegex(ValueError, 'from_data is too large'):
                    detools.bsdiff.create_patch(suffix_array,
                                                from_mmap,
                                                b'A',
                                                bytearray(1))

    def test_add_bytes_releases_buffers_on_error(self):
        first = bytearray(b'A')
        second = bytearray()

        with self.assertRaisesRegex(ValueError, 'Lengths must be equal'):
            detools.bsdiff.add_bytes(first, second)

        first.extend(b'B')
        second.extend(b'C')
        self.assertEqual(first, b'AB')
        self.assertEqual(second, b'C')


if __name__ == '__main__':
    unittest.main()
