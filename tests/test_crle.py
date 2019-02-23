import unittest

from detools.create import CrleCompressor
from detools.apply import CrleDecompressor


class DetoolsCrleTest(unittest.TestCase):

    def test_compress(self):
        datas = [
            (                       [b''], b''),
            (                      [b'A'], b'\x00\x01A'),
            (                  [5 * b'A'], b'\x00\x05AAAAA'),
            (                  [6 * b'A'], b'\x01\x06A'),
            (         [b'ABBCC', b'CBBA'], b'\x00\x09ABBCCCBBA'),
            (      [62 * b'A', b'', b'A'], b'\x01\x3fA'),
            (                 [64 * b'A'], b'\x01\x80\x01A'),
            (               [1000 * b'A'], b'\x01\xa8\x0fA'),
            (        [69999 * b'A', b'A'], b'\x01\xb0\xc5\x08A'),
            ([10 * b'A', b'BC', 8 * b'A'], b'\x01\x0aA\x00\x02BC\x01\x08A'),
            (      [10 * b'A' + 8 * b'B'], b'\x01\x0aA\x01\x08B')
        ]

        for chunks, compressed in datas:
            compressor = CrleCompressor()
            data = b''

            for chunk in chunks:
                data += compressor.compress(chunk)

            data += compressor.flush()

            self.assertEqual(data, compressed)

    def test_decompress(self):
        datas = [
            (                            [b''], b''),
            (                   [b'\x00\x01A'], b'A'),
            (             [b'\x00\x07AAAAAAA'], 7 * b'A'),
            (                   [b'\x01\x08A'], 8 * b'A'),
            (           [b'\x00\x09ABBCCCBBA'], b'ABBCCCBBA'),
            (              [b'\x01\x3f', b'A'], 63 * b'A'),
            (               [b'\x01\x80\x01A'], 64 * b'A'),
            (               [b'\x01\xa8\x0fA'], 1000 * b'A'),
            (      [b'\x01\xb0', b'\xc5\x08A'], 70000 * b'A'),
            ([b'\x01\x0aA\x00\x02BC\x01\x08A'], 10 * b'A' + b'BC' + 8 * b'A'),
            (          [b'\x01\x0aA\x01\x08B'], 10 * b'A' + 8 * b'B')
        ]

        for chunks, decompressed in datas:
            decompressor = CrleDecompressor(sum([len(c) for c in chunks]))

            for chunk in chunks:
                decompressor.decompress(chunk, 0)

            data = b''

            while True:
                byte = decompressor.decompress(b'', 1)

                if not byte:
                    break

                data += byte

            self.assertEqual(decompressor.eof, True)
            self.assertEqual(data, decompressed)


if __name__ == '__main__':
    unittest.main()
