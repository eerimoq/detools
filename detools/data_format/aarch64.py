import os
import logging
import struct
from io import BytesIO
from io import StringIO
from contextlib import redirect_stdout
import bitstruct
from ..common import file_size
from ..common import file_read
from .utils import Blocks
from .utils import create_patch_block_4_bytes as create_patch_block
from .utils import load_blocks
from .utils import format_blocks
from .utils import write_zeros_to_from_4_bytes as write_zeros_to_from


LOGGER = logging.getLogger(__name__)


class DiffReader(object):

    _CF_ADD = bitstruct.compile('u8u2u12u5u5')
    _CF_ADRP = bitstruct.compile('u1u2u5u19u5')

    def __init__(self,
                 ffrom,
                 to_size,
                 b,
                 bl,
                 add,
                 ldr,
                 adrp,
                 b_blocks,
                 bl_blocks,
                 add_blocks,
                 ldr_blocks,
                 adrp_blocks):
        self._ffrom = ffrom
        # ToDo: Calculate in read() for less memory usage.
        self._fdiff = BytesIO(b'\x00' * to_size)
        self._write_values_to_to(b_blocks, b)
        self._write_values_to_to(bl_blocks, bl)
        self._write_add_values_to_to(add_blocks, add)
        self._write_values_to_to(ldr_blocks, ldr)
        self._write_adrp_values_to_to(adrp_blocks, adrp)
        self._fdiff.seek(0)

    def read(self, size=-1):
        return self._fdiff.read(size)

    def _write_values_to_to_with_callback(self, blocks, from_dict, pack_callback):
        from_sorted = sorted(from_dict.items())

        for from_offset, to_address, values in blocks:
            from_address_base = from_sorted[from_offset][0]

            for i, value in enumerate(values):
                from_address, from_value = from_sorted[from_offset + i]
                value = pack_callback(from_value - value)
                self._fdiff.seek(to_address + from_address - from_address_base)
                self._fdiff.write(value)

    def _write_values_to_to(self, blocks, from_dict):
        self._write_values_to_to_with_callback(blocks, from_dict, self._pack_bytes)

    def _write_add_values_to_to(self, blocks, from_dict):
        self._write_values_to_to_with_callback(blocks, from_dict, self._pack_add)

    def _write_adrp_values_to_to(self, blocks, from_dict):
        self._write_values_to_to_with_callback(blocks, from_dict, self._pack_adrp)

    def _pack_bytes(self, value):
        return struct.pack('<i', value)

    def _pack_add(self, value):
        imm12 = (value & 0xfff)
        shift = ((value >> 12) & 0x3)
        r = ((value >> 14) & 0x1f)
        value = self._CF_ADD.pack(0b10010001, shift, imm12, r, r)

        return value[::-1]

    def _pack_adrp(self, value):
        immlo = (value & 0x3)
        immhi = ((value >> 2) & 0x7ffff)
        rd = ((value >> 21) & 0x1f)
        value = self._CF_ADRP.pack(0b1, immlo, 0b10000, immhi, rd)

        return value[::-1]


class FromReader(object):

    def __init__(self,
                 ffrom,
                 b,
                 bl,
                 add,
                 ldr,
                 adrp,
                 b_blocks,
                 bl_blocks,
                 add_blocks,
                 ldr_blocks,
                 adrp_blocks):
        # ToDo: Calculate in read() for less memory usage.
        self._ffrom = BytesIO(file_read(ffrom))
        write_zeros_to_from(self._ffrom, b_blocks, b)
        write_zeros_to_from(self._ffrom, bl_blocks, bl)
        write_zeros_to_from(self._ffrom, add_blocks, add)
        write_zeros_to_from(self._ffrom, ldr_blocks, ldr)
        write_zeros_to_from(self._ffrom, adrp_blocks, adrp)

    def read(self, size=-1):
        return self._ffrom.read(size)

    def seek(self, position, whence=os.SEEK_SET):
        self._ffrom.seek(position, whence)


def disassemble_b(reader, address, b):
    reader.seek(-4, os.SEEK_CUR)
    data = reader.read(4)
    b[address] = struct.unpack('<i', data)[0]


def disassemble_bl(reader, address, bl):
    reader.seek(-4, os.SEEK_CUR)
    data = reader.read(4)
    bl[address] = struct.unpack('<i', data)[0]


def disassemble_add(address, add, upper_32):
    rn = ((upper_32 >> 5) & 0x1f)
    rd = (upper_32 & 0x1f)

    if rn == rd:
        shift = ((upper_32 >> 22) & 0x3)
        imm12 = ((upper_32 >> 10) & 0xfff)
        value = imm12
        value |= (shift << 12)
        value |= (rn << 14)
        add[address] = value


def disassemble_ldr(reader, address, ldr):
    reader.seek(-4, os.SEEK_CUR)
    data = reader.read(4)
    ldr[address] = struct.unpack('<i', data)[0]


def disassemble_stp(reader, address, stp, upper_32):
    stp[address] = upper_32


def disassemble_adrp(address, adrp, upper_32):
    rd = (upper_32 & 0x1f)
    immhi = ((upper_32 >> 5) & 0x7ffff)
    immlo = ((upper_32 >> 29) & 0x3)
    value = immlo
    value |= (immhi << 2)
    value |= (rd << 21)
    adrp[address] = value


def disassemble(reader):
    """Disassembles given data and returns address-value pairs of b.w, bl,
    *ldr, *ldr.w, data pointers and code pointers.

    """

    length = file_size(reader)
    b = {}
    bl = {}
    add = {}
    ldr = {}
    #stp = {}
    adrp = {}

    while reader.tell() < length:
        address = reader.tell()
        data = reader.read(4)

        if len(data) != 4:
            LOGGER.debug('Failed to read 4 upper bytes at address 0x%x.',
                         address)
            continue

        upper_32 = struct.unpack('<I', data)[0]

        if (upper_32 & 0xfc000000) == 0x94000000:
            disassemble_bl(reader, address, bl)
        elif (upper_32 & 0xff000000) == 0x91000000:
            disassemble_add(address, add, upper_32)
        elif (upper_32 & 0xff000000) == 0x14000000:
            # disassemble_b(reader, address, b)
            pass
        elif (upper_32 & 0xffc00000) == 0xf9400000:
            disassemble_ldr(reader, address, ldr)
        #elif (upper_32 & 0xffc00000) == 0xa9000000:
        #    disassemble_stp(reader, address, stp, upper_32)
        elif (upper_32 & 0x9f000000) == 0x90000000:
            disassemble_adrp(address, adrp, upper_32)
        #elif (upper_32 & 0xffc00000) == 0xb9400000:
        #    # LDR (immediate) 32-bit
        #    disassemble_ldr(reader, address, ldr, upper_32)
        #elif (upper_32 & 0xffc00000) == 0x39400000:
        #    # LDRB (immediate) Unsigned offset
        #    disassemble_ldr(reader, address, ldr, upper_32)
        #elif (upper_32 & 0xffc00000) == 0x39000000:
        #    # LDRB (immediate) Unsigned offset
        #    disassemble_ldr(reader, address, ldr, upper_32)
        #elif (upper_32 & 0xffc00000) == 0xb9000000:
        #    # STR (immediate) 32-bit
        #    disassemble_ldr(reader, address, ldr, upper_32)
        #elif (upper_32 & 0xffe00000) == 0xf8400000:
        #    # LDUR 64-bit
        #    disassemble_ldr(reader, address, ldr, upper_32)
        #elif (upper_32 & 0xffe00000) == 0xb8400000:
        #    # LDTR 64-bit
        #    disassemble_ldr(reader, address, ldr, upper_32)
        #elif (upper_32 & 0xffc00000) == 0xf9000000:
        #    # STR (immediate) 64-bit
        #    disassemble_ldr(reader, address, ldr, upper_32)

    return b, bl, add, ldr, adrp


def encode(ffrom, fto):
    ffrom = BytesIO(file_read(ffrom))
    fto = BytesIO(file_read(fto))
    from_b, from_bl, from_add, from_ldr, from_adrp = disassemble(ffrom)
    to_b, to_bl, to_add, to_ldr, to_adrp = disassemble(fto)
    patch = create_patch_block(ffrom, fto, from_b, to_b)
    patch += create_patch_block(ffrom, fto, from_bl, to_bl)
    patch += create_patch_block(ffrom, fto, from_add, to_add)
    patch += create_patch_block(ffrom, fto, from_ldr, to_ldr)
    patch += create_patch_block(ffrom, fto, from_adrp, to_adrp)
    #patch += create_patch_block(ffrom, fto, from_stp, to_stp)

    return ffrom, fto, patch


def create_readers(ffrom, patch, to_size):
    """Return diff and from readers, used when applying a patch.

    """

    fpatch = BytesIO(patch)
    b_blocks = Blocks.from_fpatch(fpatch)
    bl_blocks = Blocks.from_fpatch(fpatch)
    add_blocks = Blocks.from_fpatch(fpatch)
    ldr_blocks = Blocks.from_fpatch(fpatch)
    adrp_blocks = Blocks.from_fpatch(fpatch)
    b, bl, add, ldr, adrp = disassemble(ffrom)
    diff_reader = DiffReader(ffrom,
                             to_size,
                             b,
                             bl,
                             add,
                             ldr,
                             adrp,
                             b_blocks,
                             bl_blocks,
                             add_blocks,
                             ldr_blocks,
                             adrp_blocks)
    from_reader = FromReader(ffrom,
                             b,
                             bl,
                             add,
                             ldr,
                             adrp,
                             b_blocks,
                             bl_blocks,
                             add_blocks,
                             ldr_blocks,
                             adrp_blocks)

    return diff_reader, from_reader


def info(patch, fsize):
    fpatch = BytesIO(patch)
    b_blocks, b_blocks_size = load_blocks(fpatch)
    bl_blocks, bl_blocks_size = load_blocks(fpatch)
    add_blocks, add_blocks_size = load_blocks(fpatch)
    ldr_blocks, ldr_blocks_size = load_blocks(fpatch)
    adrp_blocks, adrp_blocks_size = load_blocks(fpatch)
    fout = StringIO()

    with redirect_stdout(fout):
        print('Instruction:        b')
        format_blocks(b_blocks, b_blocks_size, fsize)
        print('Instruction:        bl')
        format_blocks(bl_blocks, bl_blocks_size, fsize)
        print('Instruction:        add')
        format_blocks(add_blocks, add_blocks_size, fsize)
        print('Instruction:        ldr')
        format_blocks(ldr_blocks, ldr_blocks_size, fsize)
        print('Instruction:        adrp')
        format_blocks(adrp_blocks, adrp_blocks_size, fsize)

    return fout.getvalue()
