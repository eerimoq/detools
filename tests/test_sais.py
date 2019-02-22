import unittest

import detools.csais
import detools.sais


def read_file(filename):
    with open(filename, 'rb') as fin:
        return fin.read()


class DetoolsSaisTest(unittest.TestCase):

    def test_sais(self):
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

        for data, suffix_array in datas:
            self.assertEqual(detools.csais.sais(data), suffix_array)
            self.assertEqual(detools.sais.sais(data), suffix_array)

    def test_sais_c_and_py_compatibility(self):
        datas = [
            read_file('tests/files/bad-header-magic.patch'),
            read_file('tests/files/foo-backwards.patch'),
            read_file('tests/files/foo-bad-bz2-end.patch'),
            read_file('tests/files/foo-diff-data-too-long.patch'),
            read_file('tests/files/foo-extra-data-too-long.patch'),
            read_file('tests/files/foo.new'),
            read_file('tests/files/foo-no-delta.patch'),
            read_file('tests/files/foo.old'),
            read_file('tests/files/foo.patch'),
            read_file('tests/files/foo-short.patch'),
            read_file('tests/files/micropython-esp8266-20190125-v1.10.bin')
        ]

        for data in datas:
            self.assertEqual(detools.csais.sais(data), detools.sais.sais(data))


if __name__ == '__main__':
    unittest.main()
