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
                            **kwargs):
        fpatch = BytesIO()

        with open(from_filename, 'rb') as fold:
            with open(to_filename, 'rb') as fnew:
                detools.create_patch(fold, fnew, fpatch, **kwargs)

        actual = fpatch.getvalue()
        # open(patch_filename, 'wb').write(actual)

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
                                      **kwargs):
        self.assert_create_patch(from_filename,
                                 to_filename,
                                 patch_filename,
                                 **kwargs)
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

    def test_create_and_apply_patch_foo_none_compression(self):
        self.assert_create_and_apply_patch('tests/files/foo.old',
                                           'tests/files/foo.new',
                                           'tests/files/foo-none.patch',
                                           compression='none')

    def test_create_and_apply_patch_micropython_none_compression(self):
        self.assert_create_and_apply_patch(
            'tests/files/micropython-esp8266-20180511-v1.9.4.bin',
            'tests/files/micropython-esp8266-20190125-v1.10.bin',
            'tests/files/micropython-esp8266-20180511-v1.9.4--20190125-v1.10-none.patch',
            compression='none')

    def test_create_and_apply_patch_foo_crle_compression(self):
        self.assert_create_and_apply_patch('tests/files/foo.old',
                                           'tests/files/foo.new',
                                           'tests/files/foo-crle.patch',
                                           compression='crle')

    def test_create_and_apply_patch_micropython_crle_compression(self):
        self.assert_create_and_apply_patch(
            'tests/files/micropython-esp8266-20180511-v1.9.4.bin',
            'tests/files/micropython-esp8266-20190125-v1.10.bin',
            'tests/files/micropython-esp8266-20180511-v1.9.4--20190125-v1.10-crle.patch',
            compression='crle')

    def test_create_and_apply_patch_micropython_in_place(self):
        self.assert_create_and_apply_patch(
            'tests/files/micropython-esp8266-20180511-v1.9.4.bin',
            'tests/files/micropython-esp8266-20190125-v1.10.bin',
            'tests/files/micropython-esp8266-20180511-v1.9.4--'
            '20190125-v1.10-in-place.patch',
            patch_type='in-place',
            memory_size=2097152,
            segment_size=65536)

    def test_create_and_apply_patch_foo_in_place_3000_1500(self):
        self.assert_create_and_apply_patch('tests/files/foo.old',
                                           'tests/files/foo.new',
                                           'tests/files/foo-in-place-3000-1500.patch',
                                           patch_type='in-place',
                                           memory_size=3000,
                                           segment_size=1500)

    def test_create_and_apply_patch_foo_in_place_3000_1500_1500(self):
        self.assert_create_and_apply_patch('tests/files/foo.old',
                                           'tests/files/foo.new',
                                           'tests/files/foo-in-place-3000-1500-1500.patch',
                                           patch_type='in-place',
                                           memory_size=3000,
                                           segment_size=1500,
                                           minimum_shift_size=1500)

    def test_create_and_apply_patch_foo_in_place_3000_500(self):
        self.assert_create_and_apply_patch('tests/files/foo.old',
                                           'tests/files/foo.new',
                                           'tests/files/foo-in-place-3000-500.patch',
                                           patch_type='in-place',
                                           memory_size=3000,
                                           segment_size=500)

    def test_create_and_apply_patch_foo_in_place_3000_500_crle(self):
        self.assert_create_and_apply_patch(
            'tests/files/foo.old',
            'tests/files/foo.new',
            'tests/files/foo-in-place-3000-500-crle.patch',
            patch_type='in-place',
            compression='crle',
            memory_size=3000,
            segment_size=500)

    def test_create_and_apply_patch_foo_in_place_6000_1000_crle(self):
        self.assert_create_and_apply_patch(
            'tests/files/foo.old',
            'tests/files/foo.new',
            'tests/files/foo-in-place-6000-1000-crle.patch',
            patch_type='in-place',
            compression='crle',
            memory_size=6000,
            segment_size=1000)

    def test_create_and_apply_patch_foo_in_place_minimum_size(self):
        self.assert_create_and_apply_patch(
            'tests/files/foo.old',
            'tests/files/foo.new',
            'tests/files/foo-in-place-minimum-size.patch',
            patch_type='in-place',
            memory_size=3000,
            segment_size=500,
            minimum_shift_size=2000)

    def test_create_and_apply_patch_foo_in_place_many_segments(self):
        self.assert_create_and_apply_patch(
            'tests/files/foo.old',
            'tests/files/foo.new',
            'tests/files/foo-in-place-many-segments.patch',
            patch_type='in-place',
            memory_size=3000,
            segment_size=50)

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

    def test_apply_patch_foo_short_none_compression(self):
        fnew = BytesIO()

        with open('tests/files/foo.old', 'rb') as fold:
            with open('tests/files/foo-short-none.patch', 'rb') as fpatch:
                with self.assertRaises(detools.Error) as cm:
                    detools.apply_patch(fold, fpatch, fnew)

                self.assertEqual(str(cm.exception), "Early end of patch data.")

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

    def test_apply_patch_foo_bad_patch_type(self):
        fnew = BytesIO()

        with open('tests/files/foo.old', 'rb') as fold:
            with open('tests/files/foo-bad-patch-type.patch', 'rb') as fpatch:
                with self.assertRaises(detools.Error) as cm:
                    detools.apply_patch(fold, fpatch, fnew)

                self.assertEqual(
                    str(cm.exception),
                    "Expected patch type 0 or 1, but got 7.")

    def test_apply_patch_foo_bad_compression(self):
        fnew = BytesIO()

        with open('tests/files/foo.old', 'rb') as fold:
            with open('tests/files/foo-bad-compression.patch', 'rb') as fpatch:
                with self.assertRaises(detools.Error) as cm:
                    detools.apply_patch(fold, fpatch, fnew)

                self.assertEqual(
                    str(cm.exception),
                    "Expected compression none(0), lzma(1) or crle(2), but got 15.")

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
                         'Type:               normal\n'
                         'Patch size:         177 bytes\n'
                         'To size:            2.78 KB\n'
                         'Patch/to ratio:     6.4 % (lower is better)\n'
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
                         'Type:               normal\n'
                         'Patch size:         101 bytes\n'
                         'To size:            2.78 KB\n'
                         'Patch/to ratio:     3.6 % (lower is better)\n'
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

    def test_command_line_patch_info_foo_none_compression(self):
        argv = [
            'detools',
            'patch_info',
            'tests/files/foo-none.patch'
        ]
        stdout = StringIO()

        with patch('sys.argv', argv):
            with patch('sys.stdout', stdout):
                detools._main()

        self.assertEqual(stdout.getvalue(),
                         'Type:               normal\n'
                         'Patch size:         2.8 KB\n'
                         'To size:            2.78 KB\n'
                         'Patch/to ratio:     100.6 % (lower is better)\n'
                         'Diff/extra ratio:   9828.6 % (higher is better)\n'
                         'Size/data ratio:    0.3 % (lower is better)\n'
                         'Compression:        none\n'
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

    def test_command_line_patch_info_foo_crle_compression(self):
        argv = [
            'detools',
            'patch_info',
            'tests/files/foo-crle.patch'
        ]
        stdout = StringIO()

        with patch('sys.argv', argv):
            with patch('sys.stdout', stdout):
                detools._main()

        self.assertEqual(stdout.getvalue(),
                         'Type:               normal\n'
                         'Patch size:         195 bytes\n'
                         'To size:            2.78 KB\n'
                         'Patch/to ratio:     7.0 % (lower is better)\n'
                         'Diff/extra ratio:   9828.6 % (higher is better)\n'
                         'Size/data ratio:    0.3 % (lower is better)\n'
                         'Compression:        crle\n'
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

    def test_command_line_create_patch_foo_in_place(self):
        foo_patch = 'foo-in-place-3000-1500.patch'
        argv = [
            'detools',
            'create_patch',
            '--type', 'in-place',
            '--memory-size', '3000',
            '--segment-size', '1500',
            'tests/files/foo.old',
            'tests/files/foo.new',
            foo_patch
        ]

        if os.path.exists(foo_patch):
            os.remove(foo_patch)

        with patch('sys.argv', argv):
            detools._main()

        self.assertEqual(read_file(foo_patch),
                         read_file('tests/files/foo-in-place-3000-1500.patch'))

    def test_command_line_apply_patch_foo_in_place(self):
        foo_new = 'foo.new'
        argv = [
            'detools',
            '--debug',
            'apply_patch',
            'tests/files/foo.old',
            'tests/files/foo-in-place-3000-1500.patch',
            foo_new
        ]

        if os.path.exists(foo_new):
            os.remove(foo_new)

        with patch('sys.argv', argv):
            detools._main()

        self.assertEqual(read_file(foo_new),
                         read_file('tests/files/foo.new'))

    def test_command_line_patch_info_foo_in_place(self):
        argv = [
            'detools',
            'patch_info',
            'tests/files/foo-in-place-3000-1500.patch'
        ]
        stdout = StringIO()

        with patch('sys.argv', argv):
            with patch('sys.stdout', stdout):
                detools._main()

        self.assertEqual(
            stdout.getvalue(),
            'Type:               in-place\n'
            'Number of segments: 2\n'
            'From shift size:    3000\n'
            '\n'
            '-------------------- Patch 1 --------------------\n'
            '\n'
            'From offset:        0 bytes\n'
            'Type:               normal\n'
            'Patch size:         1.2 KB\n'
            'To size:            1.5 KB\n'
            'Patch/to ratio:     79.8 % (lower is better)\n'
            'Diff/extra ratio:   0.0 % (higher is better)\n'
            'Size/data ratio:    0.3 % (lower is better)\n'
            'Compression:        lzma\n'
            '\n'
            'Number of diffs:    1\n'
            'Total diff size:    0 bytes\n'
            'Average diff size:  0 bytes\n'
            'Median diff size:   0 bytes\n'
            '\n'
            'Number of extras:   1\n'
            'Total extra size:   1.5 KB\n'
            'Average extra size: 1.5 KB\n'
            'Median extra size:  1.5 KB\n'
            '\n'
            '-------------------- Patch 2 --------------------\n'
            '\n'
            'From offset:        0 bytes\n'
            'Type:               normal\n'
            'Patch size:         1 KB\n'
            'To size:            1.28 KB\n'
            'Patch/to ratio:     78.5 % (lower is better)\n'
            'Diff/extra ratio:   0.0 % (higher is better)\n'
            'Size/data ratio:    0.3 % (lower is better)\n'
            'Compression:        lzma\n'
            '\n'
            'Number of diffs:    1\n'
            'Total diff size:    0 bytes\n'
            'Average diff size:  0 bytes\n'
            'Median diff size:   0 bytes\n'
            '\n'
            'Number of extras:   1\n'
            'Total extra size:   1.28 KB\n'
            'Average extra size: 1.28 KB\n'
            'Median extra size:  1.28 KB\n'
            '\n')


if __name__ == '__main__':
    unittest.main()
