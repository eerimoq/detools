import unittest

from detools.data_format.utils import Blocks


class DetoolsDataFormatTest(unittest.TestCase):

    def test_blocks(self):
        blocks = Blocks()

        self.assertEqual(
            repr(blocks),
            'Blocks(number_of_blocks=0, blocks=[])')

        blocks.append(0, 1, [2, 3, 4])

        self.assertEqual(
            repr(blocks),
            'Blocks(number_of_blocks=1, blocks=[Block(from_offset=0, '
            'to_address=1, number_of_values=3)])')

        self.assertEqual(blocks.to_bytes(),
                         (b'\x01\x00\x01\x03', b'\x02\x03\x04'))


if __name__ == '__main__':
    unittest.main()
