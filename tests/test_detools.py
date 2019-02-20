import unittest
from io import BytesIO

import detools


class DetoolsTest(unittest.TestCase):

    def test_create_patch_foo(self):
        fpatch = BytesIO()

        with open('tests/files/foo.old', 'rb') as fold:
            with open('tests/files/foo.new', 'rb') as fnew:
                detools.create_patch(fold, fnew, fpatch)

        actual = fpatch.getvalue()

        with open('tests/files/foo.patch', 'rb') as fpatch:
            expected = fpatch.read()

        self.assertEqual(actual, expected)

    def test_apply_patch_foo(self):
        fnew = BytesIO()

        with open('tests/files/foo.old', 'rb') as fold:
            with open('tests/files/foo.patch', 'rb') as fpatch:
                detools.apply_patch(fold, fpatch, fnew)

        actual = fnew.getvalue()

        with open('tests/files/foo.new', 'rb') as fnew:
            expected = fnew.read()

        self.assertEqual(actual, expected)

    def test_apply_patch_bad_header_magic(self):
        fnew = BytesIO()

        with open('tests/files/foo.old', 'rb') as fold:
            with open('tests/files/bad-header-magic.patch', 'rb') as fpatch:
                with self.assertRaises(detools.Error) as cm:
                    detools.apply_patch(fold, fpatch, fnew)

                self.assertEqual(
                    str(cm.exception),
                    "Expected header magic b'detools0', but got b'eetools0'.")

    def test_apply_patch_empty(self):
        fnew = BytesIO()

        with open('tests/files/foo.old', 'rb') as fold:
            with open('tests/files/empty.patch', 'rb') as fpatch:
                with self.assertRaises(detools.Error) as cm:
                    detools.apply_patch(fold, fpatch, fnew)

                self.assertEqual(str(cm.exception),
                                 "Failed to read the patch header.")

    def test_apply_patch_foo_short(self):
        fnew = BytesIO()

        with open('tests/files/foo.old', 'rb') as fold:
            with open('tests/files/foo-short.patch', 'rb') as fpatch:
                with self.assertRaises(detools.Error) as cm:
                    detools.apply_patch(fold, fpatch, fnew)

                self.assertEqual(str(cm.exception),
                                 "End of patch not found.")

    def test_apply_patch_foo_long(self):
        fnew = BytesIO()

        with open('tests/files/foo.old', 'rb') as fold:
            with open('tests/files/foo-bad-bz2-end.patch', 'rb') as fpatch:
                with self.assertRaises(detools.Error) as cm:
                    detools.apply_patch(fold, fpatch, fnew)

                self.assertEqual(str(cm.exception),
                                 "Patch decompression failed.")

    def test_apply_patch_foo_diff_data_too_long(self):
        fnew = BytesIO()

        with open('tests/files/foo.old', 'rb') as fold:
            with open('tests/files/foo-diff-data-too-long.patch', 'rb') as fpatch:
                with self.assertRaises(detools.Error) as cm:
                    detools.apply_patch(fold, fpatch, fnew)

                self.assertEqual(str(cm.exception),
                                 "Patch diff data too long.")

    def test_apply_patch_foo_extra_data_too_long(self):
        fnew = BytesIO()

        with open('tests/files/foo.old', 'rb') as fold:
            with open('tests/files/foo-extra-data-too-long.patch', 'rb') as fpatch:
                with self.assertRaises(detools.Error) as cm:
                    detools.apply_patch(fold, fpatch, fnew)

                self.assertEqual(str(cm.exception),
                                 "Patch extra data too long.")


if __name__ == '__main__':
    unittest.main()
