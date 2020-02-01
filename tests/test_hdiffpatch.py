import unittest
import struct

import detools.hdiffpatch


def read_file(filename):
    with open(filename, 'rb') as fin:
        return fin.read()


class DetoolsHDiffPatchTest(unittest.TestCase):

    maxDiff = None

    def test_diff_patch(self):
        diff = detools.hdiffpatch.create_patch(read_file('tests/files/foo/old'),
                                               read_file('tests/files/foo/new'),
                                               0)
        self.assertEqual(diff, read_file('tests/files/foo/hdiffpatch.patch'))
        to = detools.hdiffpatch.apply_patch(read_file('tests/files/foo/old'),
                                            bytes(diff))
        self.assertEqual(to, read_file('tests/files/foo/new'))


if __name__ == '__main__':
    unittest.main()
