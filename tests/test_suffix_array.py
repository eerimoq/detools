import unittest
import struct
import mmap
import tempfile
from contextlib import contextmanager

import detools.sais


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


class DetoolsSuffixArrayTest(unittest.TestCase):

    def test_suffix_array(self):
        datas = [
            (
                b'',
                [0]
            ),
            (
                b'1',
                [1, 0]
            ),
            (
                b'1234',
                [4, 0, 1, 2, 3]
            ),
            (
                b'55555555',
                [8, 7, 6, 5, 4, 3, 2, 1, 0]
            ),
            (
                b'adska9kkkoaofeopkjvuuuuewflk-0920314923fg',
                [
                    41, 28, 32, 29, 34, 31, 37, 33, 38, 35,
                    30, 36,  5,  4,  0, 10,  1, 13, 23, 12,
                    39, 25, 40, 17, 27,  3, 16,  6,  7,  8,
                    26,  9, 11, 14, 15,  2, 22, 21, 20, 19,
                    18, 24
                ]
            )
        ]

        for data, expected in datas:
            expected = suffix_array_list_to_bytearray(expected)
            suffix_array = bytearray(len(expected))

            detools.suffix_array.sais(data, suffix_array)
            self.assertEqual(suffix_array, expected)

            detools.suffix_array.divsufsort(data, suffix_array)
            self.assertEqual(suffix_array, expected)

    def test_suffix_array_rejects_too_small_output_buffer(self):
        with self.assertRaisesRegex(ValueError, 'Suffix array buffer is too small'):
            detools.suffix_array.sais(b'A', bytearray(4))

    def test_suffix_array_rejects_input_larger_than_int32(self):
        huge_size = 2 ** 31
        suffix_array_size = 4 * (huge_size + 1)

        with sparse_mmap(huge_size, mmap.ACCESS_READ) as data:
            with sparse_mmap(suffix_array_size, mmap.ACCESS_WRITE) as suffix_array:
                with self.assertRaisesRegex(ValueError, 'from_data is too large'):
                    detools.suffix_array.divsufsort(data, suffix_array)


if __name__ == '__main__':
    unittest.main()
