import os
import unittest
from unittest.mock import patch
from io import StringIO

import detools


def read_file(filename):
    with open(filename, 'rb') as fin:
        return fin.read()


class DetoolsCommandLineTest(unittest.TestCase):

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
                         'Patch size:         126 bytes\n'
                         'To size:            2.71 KiB\n'
                         'Patch/to ratio:     4.5 % (lower is better)\n'
                         'Diff/extra ratio:   9828.6 % (higher is better)\n'
                         'Size/data ratio:    0.3 % (lower is better)\n'
                         'Compression:        lzma\n'
                         '\n'
                         'Number of diffs:    2\n'
                         'Total diff size:    2.69 KiB\n'
                         'Average diff size:  1.34 KiB\n'
                         'Median diff size:   1.34 KiB\n'
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
                         'Patch size:         48 bytes\n'
                         'To size:            2.71 KiB\n'
                         'Patch/to ratio:     1.7 % (lower is better)\n'
                         'Diff/extra ratio:   inf % (higher is better)\n'
                         'Size/data ratio:    0.2 % (lower is better)\n'
                         'Compression:        lzma\n'
                         '\n'
                         'Number of diffs:    1\n'
                         'Total diff size:    2.71 KiB\n'
                         'Average diff size:  2.71 KiB\n'
                         'Median diff size:   2.71 KiB\n'
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
                         'Patch size:         2.73 KiB\n'
                         'To size:            2.71 KiB\n'
                         'Patch/to ratio:     100.4 % (lower is better)\n'
                         'Diff/extra ratio:   9828.6 % (higher is better)\n'
                         'Size/data ratio:    0.3 % (lower is better)\n'
                         'Compression:        none\n'
                         '\n'
                         'Number of diffs:    2\n'
                         'Total diff size:    2.69 KiB\n'
                         'Average diff size:  1.34 KiB\n'
                         'Median diff size:   1.34 KiB\n'
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
                         'Patch size:         189 bytes\n'
                         'To size:            2.71 KiB\n'
                         'Patch/to ratio:     6.8 % (lower is better)\n'
                         'Diff/extra ratio:   9828.6 % (higher is better)\n'
                         'Size/data ratio:    0.3 % (lower is better)\n'
                         'Compression:        crle\n'
                         '\n'
                         'Number of diffs:    2\n'
                         'Total diff size:    2.69 KiB\n'
                         'Average diff size:  1.34 KiB\n'
                         'Median diff size:   1.34 KiB\n'
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
        foo_mem = 'foo.mem'
        argv = [
            'detools',
            '--debug',
            'apply_patch_in_place',
            foo_mem,
            'tests/files/foo-in-place-3000-1500.patch'
        ]

        with open(foo_mem, 'wb') as fmem:
            with open('tests/files/foo.old', 'rb') as fold:
                fmem.write(fold.read() + (3000 - 2780) * b'\xff')

        with patch('sys.argv', argv):
            detools._main()

        self.assertEqual(
            read_file(foo_mem),
            read_file('tests/files/foo.new') + (3000 - 2780) * b'\xff')

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
            'Patch size:         1.91 KiB\n'
            'Memory size:        2.93 KiB\n'
            'Segment size:       1.46 KiB\n'
            'From shift size:    2.93 KiB\n'
            'From size:          2.71 KiB\n'
            'To size:            2.71 KiB\n'
            'Patch/to ratio:     70.3 % (lower is better)\n'
            'Number of segments: 2\n'
            'Compression:        lzma\n'
            '\n'
            '------------------- Segment 1 -------------------\n'
            '\n'
            'From range:         0 bytes - 0 bytes\n'
            'To range:           0 bytes - 1.46 KiB\n'
            'Diff/extra ratio:   0.0 % (higher is better)\n'
            'Size/data ratio:    0.3 % (lower is better)\n'
            '\n'
            'Number of diffs:    1\n'
            'Total diff size:    0 bytes\n'
            'Average diff size:  0 bytes\n'
            'Median diff size:   0 bytes\n'
            '\n'
            'Number of extras:   1\n'
            'Total extra size:   1.46 KiB\n'
            'Average extra size: 1.46 KiB\n'
            'Median extra size:  1.46 KiB\n'
            '\n'
            '------------------- Segment 2 -------------------\n'
            '\n'
            'From range:         0 bytes - 0 bytes\n'
            'To range:           1.46 KiB - 2.71 KiB\n'
            'Diff/extra ratio:   0.0 % (higher is better)\n'
            'Size/data ratio:    0.3 % (lower is better)\n'
            '\n'
            'Number of diffs:    1\n'
            'Total diff size:    0 bytes\n'
            'Average diff size:  0 bytes\n'
            'Median diff size:   0 bytes\n'
            '\n'
            'Number of extras:   1\n'
            'Total extra size:   1.25 KiB\n'
            'Average extra size: 1.25 KiB\n'
            'Median extra size:  1.25 KiB\n'
            '\n')

    def test_command_line_patch_info_foo_in_place_no_human(self):
        argv = [
            'detools',
            'patch_info',
            '--no-human',
            'tests/files/foo-in-place-3000-1500.patch'
        ]
        stdout = StringIO()

        with patch('sys.argv', argv):
            with patch('sys.stdout', stdout):
                detools._main()

        self.assertEqual(
            stdout.getvalue(),
            'Type:               in-place\n'
            'Patch size:         1954 bytes\n'
            'Memory size:        3000 bytes\n'
            'Segment size:       1500 bytes\n'
            'From shift size:    3000 bytes\n'
            'From size:          2780 bytes\n'
            'To size:            2780 bytes\n'
            'Patch/to ratio:     70.3 % (lower is better)\n'
            'Number of segments: 2\n'
            'Compression:        lzma\n'
            '\n'
            '------------------- Segment 1 -------------------\n'
            '\n'
            'From range:         0 bytes - 0 bytes\n'
            'To range:           0 bytes - 1500 bytes\n'
            'Diff/extra ratio:   0.0 % (higher is better)\n'
            'Size/data ratio:    0.3 % (lower is better)\n'
            '\n'
            'Number of diffs:    1\n'
            'Total diff size:    0 bytes\n'
            'Average diff size:  0 bytes\n'
            'Median diff size:   0 bytes\n'
            '\n'
            'Number of extras:   1\n'
            'Total extra size:   1500 bytes\n'
            'Average extra size: 1500 bytes\n'
            'Median extra size:  1500 bytes\n'
            '\n'
            '------------------- Segment 2 -------------------\n'
            '\n'
            'From range:         0 bytes - 0 bytes\n'
            'To range:           1500 bytes - 2780 bytes\n'
            'Diff/extra ratio:   0.0 % (higher is better)\n'
            'Size/data ratio:    0.3 % (lower is better)\n'
            '\n'
            'Number of diffs:    1\n'
            'Total diff size:    0 bytes\n'
            'Average diff size:  0 bytes\n'
            'Median diff size:   0 bytes\n'
            '\n'
            'Number of extras:   1\n'
            'Total extra size:   1280 bytes\n'
            'Average extra size: 1280 bytes\n'
            'Median extra size:  1280 bytes\n'
            '\n')

    def test_command_line_create_patch_foo_in_place_size_units(self):
        foo_patch = 'foo-in-place-3k-1.5k.patch'
        argv = [
            'detools',
            'create_patch',
            '--type', 'in-place',
            '--memory-size', '3k',
            '--segment-size', '1.5k',
            'tests/files/foo.old',
            'tests/files/foo.new',
            foo_patch
        ]

        if os.path.exists(foo_patch):
            os.remove(foo_patch)

        with patch('sys.argv', argv):
            detools._main()

        self.assertEqual(read_file(foo_patch),
                         read_file('tests/files/foo-in-place-3k-1.5k.patch'))

    def test_command_line_apply_patch_foo_in_place_size_units(self):
        foo_mem = 'foo.mem'
        argv = [
            'detools',
            '--debug',
            'apply_patch_in_place',
            foo_mem,
            'tests/files/foo-in-place-3k-1.5k.patch'
        ]

        with open(foo_mem, 'wb') as fmem:
            with open('tests/files/foo.old', 'rb') as fold:
                fmem.write(fold.read() + (3072 - 2780) * b'\xff')

        with patch('sys.argv', argv):
            detools._main()

        self.assertEqual(
            read_file(foo_mem),
            read_file('tests/files/foo.new') + (3072 - 2780) * b'\xff')

    def test_command_line_patch_info_foo_in_place_size_units(self):
        argv = [
            'detools',
            'patch_info',
            'tests/files/foo-in-place-3k-1.5k.patch'
        ]
        stdout = StringIO()

        with patch('sys.argv', argv):
            with patch('sys.stdout', stdout):
                detools._main()

        self.assertEqual(
            stdout.getvalue(),
            'Type:               in-place\n'
            'Patch size:         1.91 KiB\n'
            'Memory size:        3 KiB\n'
            'Segment size:       1.5 KiB\n'
            'From shift size:    3 KiB\n'
            'From size:          2.71 KiB\n'
            'To size:            2.71 KiB\n'
            'Patch/to ratio:     70.2 % (lower is better)\n'
            'Number of segments: 2\n'
            'Compression:        lzma\n'
            '\n'
            '------------------- Segment 1 -------------------\n'
            '\n'
            'From range:         0 bytes - 0 bytes\n'
            'To range:           0 bytes - 1.5 KiB\n'
            'Diff/extra ratio:   0.0 % (higher is better)\n'
            'Size/data ratio:    0.3 % (lower is better)\n'
            '\n'
            'Number of diffs:    1\n'
            'Total diff size:    0 bytes\n'
            'Average diff size:  0 bytes\n'
            'Median diff size:   0 bytes\n'
            '\n'
            'Number of extras:   1\n'
            'Total extra size:   1.5 KiB\n'
            'Average extra size: 1.5 KiB\n'
            'Median extra size:  1.5 KiB\n'
            '\n'
            '------------------- Segment 2 -------------------\n'
            '\n'
            'From range:         0 bytes - 0 bytes\n'
            'To range:           1.5 KiB - 2.71 KiB\n'
            'Diff/extra ratio:   0.0 % (higher is better)\n'
            'Size/data ratio:    0.3 % (lower is better)\n'
            '\n'
            'Number of diffs:    1\n'
            'Total diff size:    0 bytes\n'
            'Average diff size:  0 bytes\n'
            'Median diff size:   0 bytes\n'
            '\n'
            'Number of extras:   1\n'
            'Total extra size:   1.21 KiB\n'
            'Average extra size: 1.21 KiB\n'
            'Median extra size:  1.21 KiB\n'
            '\n')

    def test_command_line_patch_info_empty(self):
        argv = [
            'detools',
            'patch_info',
            'tests/files/empty.patch'
        ]
        stdout = StringIO()

        with patch('sys.argv', argv):
            with patch('sys.stdout', stdout):
                detools._main()

        self.assertEqual(
            stdout.getvalue(),
            'Type:               normal\n'
            'Patch size:         2 bytes\n'
            'To size:            0 bytes\n'
            'Patch/to ratio:     inf % (lower is better)\n'
            'Diff/extra ratio:   inf % (higher is better)\n'
            'Size/data ratio:    inf % (lower is better)\n'
            'Compression:        lzma\n'
            '\n'
            'Number of diffs:    0\n'
            'Total diff size:    0 bytes\n'
            'Average diff size:  -\n'
            'Median diff size:   -\n'
            '\n'
            'Number of extras:   0\n'
            'Total extra size:   0 bytes\n'
            'Average extra size: -\n'
            'Median extra size:  -\n')

    def test_command_line_patch_info_empty_in_place(self):
        argv = [
            'detools',
            'patch_info',
            'tests/files/empty-in-place.patch'
        ]
        stdout = StringIO()

        with patch('sys.argv', argv):
            with patch('sys.stdout', stdout):
                detools._main()

        self.assertEqual(
            stdout.getvalue(),
            'Type:               in-place\n'
            'Patch size:         11 bytes\n'
            'Memory size:        29.3 KiB\n'
            'Segment size:       500 bytes\n'
            'From shift size:    29.3 KiB\n'
            'From size:          0 bytes\n'
            'To size:            0 bytes\n'
            'Patch/to ratio:     inf % (lower is better)\n'
            'Number of segments: 0\n'
            'Compression:        lzma\n'
            '\n')


if __name__ == '__main__':
    unittest.main()
