import unittest
from unittest.mock import patch
from io import BytesIO

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

    def assert_apply_patch(self,
                           from_filename,
                           to_filename,
                           patch_filename,
                           patch_type):
        if patch_type == 'normal':
            fnew = BytesIO()

            with open(from_filename, 'rb') as fold:
                with open(patch_filename, 'rb') as fpatch:
                    to_size = detools.apply_patch(fold, fpatch, fnew)

            actual = fnew.getvalue()
        elif patch_type == 'in-place':
            with open(from_filename, 'rb') as fold:
                fmem = BytesIO(fold.read())

            with open(patch_filename, 'rb') as fpatch:
                to_size = detools.apply_patch_in_place(fmem, fpatch)

            actual = fmem.getvalue()
        else:
            raise Exception(patch_type)

        with open(to_filename, 'rb') as fnew:
            expected = fnew.read()

        self.assertEqual(to_size, len(expected))
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

        self.assert_apply_patch(from_filename,
                                to_filename,
                                patch_filename,
                                kwargs.get('patch_type', 'normal'))

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
            'tests/files/micropython-esp8266-20180511-v1.9.4--'
            '20190125-v1.10-none.patch',
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
        self.assert_create_and_apply_patch(
            'tests/files/foo.old',
            'tests/files/foo.new',
            'tests/files/foo-in-place-3000-1500.patch',
            patch_type='in-place',
            memory_size=3000,
            segment_size=1500)

    def test_create_and_apply_patch_foo_in_place_3k_1_5k(self):
        self.assert_create_and_apply_patch('tests/files/foo.old',
                                           'tests/files/foo.new',
                                           'tests/files/foo-in-place-3k-1.5k.patch',
                                           patch_type='in-place',
                                           memory_size=3072,
                                           segment_size=1536)

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

    def test_create_and_apply_patch_empty(self):
        self.assert_create_and_apply_patch('tests/files/empty.old',
                                           'tests/files/empty.new',
                                           'tests/files/empty.patch')

    def test_create_and_apply_patch_empty_none_compression(self):
        self.assert_create_and_apply_patch('tests/files/empty.old',
                                           'tests/files/empty.new',
                                           'tests/files/empty-none.patch',
                                           compression='none')

    def test_create_and_apply_patch_empty_crle_compression(self):
        self.assert_create_and_apply_patch('tests/files/empty.old',
                                           'tests/files/empty.new',
                                           'tests/files/empty-crle.patch',
                                           compression='crle')

    def test_create_and_apply_patch_empty_in_place(self):
        self.assert_create_and_apply_patch('tests/files/empty.old',
                                           'tests/files/empty.new',
                                           'tests/files/empty-in-place.patch',
                                           patch_type='in-place',
                                           memory_size=30000,
                                           segment_size=500)

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
                    "Expected patch type 0, but got 7.")

    def test_create_patch_foo_bad_patch_type(self):
        fpatch = BytesIO()

        with open('tests/files/foo.old', 'rb') as fold:
            with open('tests/files/foo.new', 'rb') as fnew:
                with self.assertRaises(detools.Error) as cm:
                    detools.create_patch(fold, fnew, fpatch, patch_type='bad')

                self.assertEqual(str(cm.exception), "Bad patch type 'bad'.")

    def test_apply_patch_foo_bad_compression(self):
        fnew = BytesIO()

        with open('tests/files/foo.old', 'rb') as fold:
            with open('tests/files/foo-bad-compression.patch', 'rb') as fpatch:
                with self.assertRaises(detools.Error) as cm:
                    detools.apply_patch(fold, fpatch, fnew)

                self.assertEqual(
                    str(cm.exception),
                    "Expected compression none(0), lzma(1) or crle(2), but got 15.")

    def test_create_patch_foo_bad_compression(self):
        fpatch = BytesIO()

        with open('tests/files/foo.old', 'rb') as fold:
            with open('tests/files/foo.new', 'rb') as fnew:
                with self.assertRaises(detools.Error) as cm:
                    detools.create_patch(fold, fnew, fpatch, compression='bad')

                self.assertEqual(
                    str(cm.exception),
                    "Expected compression crle, lzma or none, but got bad.")

    def test_apply_patch_one_byte(self):
        fnew = BytesIO()

        with open('tests/files/foo.old', 'rb') as fold:
            with open('tests/files/foo-one-byte.patch', 'rb') as fpatch:
                with self.assertRaises(detools.Error) as cm:
                    detools.apply_patch(fold, fpatch, fnew)

                self.assertEqual(str(cm.exception),
                                 "Failed to read first size byte.")

    def test_apply_patch_short_to_size(self):
        fnew = BytesIO()

        with open('tests/files/foo.old', 'rb') as fold:
            with open('tests/files/foo-short-to-size.patch', 'rb') as fpatch:
                with self.assertRaises(detools.Error) as cm:
                    detools.apply_patch(fold, fpatch, fnew)

                self.assertEqual(str(cm.exception),
                                 "Failed to read consecutive size byte.")

    def test_create_patch_in_place_bad_memory_and_segment_size_ratio(self):
        fpatch = BytesIO()

        with open('tests/files/foo.old', 'rb') as fold:
            with open('tests/files/foo.new', 'rb') as fnew:
                with self.assertRaises(detools.Error) as cm:
                    detools.create_patch(fold,
                                         fnew,
                                         fpatch,
                                         patch_type='in-place',
                                         memory_size=3000,
                                         segment_size=501)

                self.assertEqual(
                    str(cm.exception),
                    "Memory size 3000 is not a multiple of segment size 501.")

    def test_create_patch_in_place_bad_minimum_shift_and_segment_size_ratio(self):
        fpatch = BytesIO()

        with open('tests/files/foo.old', 'rb') as fold:
            with open('tests/files/foo.new', 'rb') as fnew:
                with self.assertRaises(detools.Error) as cm:
                    detools.create_patch(fold,
                                         fnew,
                                         fpatch,
                                         patch_type='in-place',
                                         memory_size=3000,
                                         segment_size=500,
                                         minimum_shift_size=999)

                self.assertEqual(
                    str(cm.exception),
                    "Minimum shift size 999 is not a multiple of segment size 500.")

    def test_patch_info_bad_empty_header(self):
        with self.assertRaises(detools.Error) as cm:
            detools.patch_info_filename('tests/files/empty.old')

        self.assertEqual(str(cm.exception), "Failed to read the patch header.")

    def test_patch_info_bad_patch_type(self):
        with self.assertRaises(detools.Error) as cm:
            detools.patch_info_filename('tests/files/foo-bad-patch-type.patch')

        self.assertEqual(str(cm.exception), "Bad patch type 7.")


if __name__ == '__main__':
    unittest.main()
