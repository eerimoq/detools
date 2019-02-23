import os
import unittest
from unittest.mock import patch
from io import BytesIO
from io import StringIO

import detools


def read_file(filename):
    with open(filename, 'rb') as fin:
        return fin.read()


class DetoolsTest(unittest.TestCase):

    def assert_create_patch(self,
                            from_filename,
                            to_filename,
                            patch_filename,
                            compression):
        fpatch = BytesIO()

        with open(from_filename, 'rb') as fold:
            with open(to_filename, 'rb') as fnew:
                detools.create_patch(fold, fnew, fpatch, compression)

        actual = fpatch.getvalue()

        with open(patch_filename, 'rb') as fpatch:
            expected = fpatch.read()

        self.assertEqual(actual, expected)

    def assert_apply_patch(self, from_filename, to_filename, patch_filename):
        fnew = BytesIO()

        with open(from_filename, 'rb') as fold:
            with open(patch_filename, 'rb') as fpatch:
                detools.apply_patch(fold, fpatch, fnew)

        actual = fnew.getvalue()

        with open(to_filename, 'rb') as fnew:
            expected = fnew.read()

        self.assertEqual(actual, expected)

    def assert_create_and_apply_patch(self,
                                      from_filename,
                                      to_filename,
                                      patch_filename,
                                      compression='lzma'):
        self.assert_create_patch(from_filename,
                                 to_filename,
                                 patch_filename,
                                 compression)
        self.assert_apply_patch(from_filename, to_filename, patch_filename)

    def test_create_and_apply_patch_foo(self):
        self.assert_create_and_apply_patch('tests/files/foo.old',
                                           'tests/files/foo.new',
                                           'tests/files/foo.patch')

    def test_create_and_apply_patch_foo_backwards(self):
        self.assert_create_and_apply_patch('tests/files/foo.new',
                                           'tests/files/foo.old',
                                           'tests/files/foo-backwards.patch')

    def test_create_and_apply_patch_micropython(self):
        self.assert_create_and_apply_patch(
            'tests/files/micropython-esp8266-20180511-v1.9.4.bin',
            'tests/files/micropython-esp8266-20190125-v1.10.bin',
            'tests/files/micropython-esp8266-20180511-v1.9.4--20190125-v1.10.patch')

    def test_create_and_apply_patch_micropython_none_compression(self):
        self.assert_create_and_apply_patch(
            'tests/files/micropython-esp8266-20180511-v1.9.4.bin',
            'tests/files/micropython-esp8266-20190125-v1.10.bin',
            'tests/files/micropython-esp8266-20180511-v1.9.4--20190125-v1.10-none.patch',
            compression='none')

    def test_create_and_apply_patch_bsdiff(self):
        self.assert_create_and_apply_patch(
            'tests/files/bsdiff.py',
            'tests/files/READ-ME.rst',
            'tests/files/bsdiff-READ-ME.patch')

    def test_create_and_apply_patch_sais(self):
        self.assert_create_and_apply_patch(
            'tests/files/sais.c',
            'tests/files/READ-ME.rst',
            'tests/files/sais-READ-ME.patch')

    def test_create_and_apply_patch_3f5531ba56182a807a5c358f04678b3b026d3a(self):
        self.assert_create_and_apply_patch(
            'tests/files/3f5531ba56182a807a5c358f04678b3b026d3a.bin',
            'tests/files/READ-ME.rst',
            'tests/files/3f5531ba56182a807a5c358f04678b3b026d3a-READ-ME.patch')

    def test_create_and_apply_patch_b2db59ab76ca36f67e61f720857021df8a660b(self):
        self.assert_create_and_apply_patch(
            'tests/files/b2db59ab76ca36f67e61f720857021df8a660b.bin',
            'tests/files/READ-ME.rst',
            'tests/files/b2db59ab76ca36f67e61f720857021df8a660b-READ-ME.patch')

    def test_create_and_apply_patch_d027a1e1f752f15b6a13d9f9d775f3914c83f7(self):
        self.assert_create_and_apply_patch(
            'tests/files/d027a1e1f752f15b6a13d9f9d775f3914c83f7.bin',
            'tests/files/READ-ME.rst',
            'tests/files/d027a1e1f752f15b6a13d9f9d775f3914c83f7-READ-ME.patch')

    def test_create_and_apply_patch_eb9ed88e9975028c4694e070cfaece2498e92d(self):
        self.assert_create_and_apply_patch(
            'tests/files/eb9ed88e9975028c4694e070cfaece2498e92d.bin',
            'tests/files/READ-ME.rst',
            'tests/files/eb9ed88e9975028c4694e070cfaece2498e92d-READ-ME.patch')

    def test_create_and_apply_patch_no_delta(self):
        self.assert_create_and_apply_patch('tests/files/foo.new',
                                           'tests/files/foo.new',
                                           'tests/files/foo-no-delta.patch')

    def test_apply_patch_bad_header_magic(self):
        fnew = BytesIO()

        with open('tests/files/foo.old', 'rb') as fold:
            with open('tests/files/bad-header-magic.patch', 'rb') as fpatch:
                with self.assertRaises(detools.Error) as cm:
                    detools.apply_patch(fold, fpatch, fnew)

                self.assertEqual(
                    str(cm.exception),
                    "Expected header magic b'detools', but got b'eetools'.")

    def test_apply_patch_empty(self):
        fnew = BytesIO()

        with open('tests/files/foo.old', 'rb') as fold:
            with open('tests/files/foo-empty.patch', 'rb') as fpatch:
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
            with open('tests/files/foo-bad-lzma-end.patch', 'rb') as fpatch:
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

    def test_apply_patch_foo_bad_kind(self):
        fnew = BytesIO()

        with open('tests/files/foo.old', 'rb') as fold:
            with open('tests/files/foo-bad-kind.patch', 'rb') as fpatch:
                with self.assertRaises(detools.Error) as cm:
                    detools.apply_patch(fold, fpatch, fnew)

                self.assertEqual(str(cm.exception),
                                 "Expected kind 48, but got 57.")

    def test_apply_patch_foo_non_ascii_compression(self):
        fnew = BytesIO()

        with open('tests/files/foo.old', 'rb') as fold:
            with open('tests/files/foo-non-ascii-compression.patch', 'rb') as fpatch:
                with self.assertRaises(detools.Error) as cm:
                    detools.apply_patch(fold, fpatch, fnew)

                self.assertEqual(
                    str(cm.exception),
                    "Failed to decode the compression field in the header "
                    "(got b'\\xdczma').")

    def test_apply_patch_foo_bad_compression(self):
        fnew = BytesIO()

        with open('tests/files/foo.old', 'rb') as fold:
            with open('tests/files/foo-bad-compression.patch', 'rb') as fpatch:
                with self.assertRaises(detools.Error) as cm:
                    detools.apply_patch(fold, fpatch, fnew)

                self.assertEqual(
                    str(cm.exception),
                    "Expected compression 'lzma' or 'none', but got 'abcd'.")

    def test_command_line_create_patch_foo(self):
        foo_patch = 'foo.patch'
        argv = [
            'detools',
            'create_patch',
            'tests/files/foo.old',
            'tests/files/foo.new',
            foo_patch
        ]

        if os.path.exists(foo_patch):
            os.remove(foo_patch)

        with patch('sys.argv', argv):
            detools._main()

        self.assertEqual(read_file(foo_patch),
                         read_file('tests/files/foo.patch'))

    def test_command_line_apply_patch_foo(self):
        foo_new = 'foo.new'
        argv = [
            'detools',
            '--debug',
            'apply_patch',
            'tests/files/foo.old',
            'tests/files/foo.patch',
            foo_new
        ]

        if os.path.exists(foo_new):
            os.remove(foo_new)

        with patch('sys.argv', argv):
            detools._main()

        self.assertEqual(read_file(foo_new),
                         read_file('tests/files/foo.new'))

    def test_command_line_patch_info_foo(self):
        argv = [
            'detools',
            'patch_info',
            'tests/files/foo.patch'
        ]
        stdout = StringIO()

        with patch('sys.argv', argv):
            with patch('sys.stdout', stdout):
                detools._main()

        self.assertEqual(stdout.getvalue(),
                         'Patch size:         188 bytes\n'
                         'To size:            2.78 KB\n'
                         'Patch/to ratio:     6.8 % (lower is better)\n'
                         'Diff/extra ratio:   9828.6 % (higher is better)\n'
                         'Size/data ratio:    0.3 % (lower is better)\n'
                         'Compression:        lzma\n'
                         '\n'
                         'Number of diffs:    2\n'
                         'Total diff size:    2.75 KB\n'
                         'Average diff size:  1.38 KB\n'
                         'Median diff size:   1.38 KB\n'
                         '\n'
                         'Number of extras:   2\n'
                         'Total extra size:   28 bytes\n'
                         'Average extra size: 14 bytes\n'
                         'Median extra size:  14 bytes\n')

    def test_command_line_patch_info_foo_no_delta(self):
        argv = [
            'detools',
            'patch_info',
            'tests/files/foo-no-delta.patch'
        ]
        stdout = StringIO()

        with patch('sys.argv', argv):
            with patch('sys.stdout', stdout):
                detools._main()

        self.assertEqual(stdout.getvalue(),
                         'Patch size:         112 bytes\n'
                         'To size:            2.78 KB\n'
                         'Patch/to ratio:     4.0 % (lower is better)\n'
                         'Diff/extra ratio:   inf % (higher is better)\n'
                         'Size/data ratio:    0.2 % (lower is better)\n'
                         'Compression:        lzma\n'
                         '\n'
                         'Number of diffs:    1\n'
                         'Total diff size:    2.78 KB\n'
                         'Average diff size:  2.78 KB\n'
                         'Median diff size:   2.78 KB\n'
                         '\n'
                         'Number of extras:   1\n'
                         'Total extra size:   0 bytes\n'
                         'Average extra size: 0 bytes\n'
                         'Median extra size:  0 bytes\n')


if __name__ == '__main__':
    unittest.main()
