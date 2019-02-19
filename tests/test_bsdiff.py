import unittest
from io import BytesIO

import bsdiff


class BsdiffTest(unittest.TestCase):

    def test_patch_foo(self):
        fnew = BytesIO()

        with open('tests/files/foo.old', 'rb') as fold:
            with open('tests/files/foo.patch', 'rb') as fpatch:
                bsdiff.patch(fold, fpatch, fnew)

        actual = fnew.getvalue()

        with open('tests/files/foo.new', 'rb') as fnew:
            expected = fnew.read()

        self.assertEqual(actual, expected)

    def test_patch_bad_header_magic(self):
        fnew = BytesIO()

        with open('tests/files/foo.old', 'rb') as fold:
            with open('tests/files/bad-header-magic.patch', 'rb') as fpatch:
                with self.assertRaises(bsdiff.Error) as cm:
                    bsdiff.patch(fold, fpatch, fnew)

                self.assertEqual(
                    str(cm.exception),
                    "Expected header magic b'bsdiff01', but got b'csdiff01'.")


if __name__ == '__main__':
    unittest.main()
