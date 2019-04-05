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
from .utils import DiffReader as UtilsDiffReader
from .utils import FromReader as UtilsFromReader
from .utils import create_patch_block_4_bytes as create_patch_block
from .utils import load_blocks
from .utils import format_blocks


LOGGER = logging.getLogger(__name__)


class DiffReader(UtilsDiffReader):

    _CF_ADD = bitstruct.compile('u8u2u12u5u5')
    _CF_ADRP = bitstruct.compile('u1u2u5u19u5')

    def __init__(self,
                 ffrom,
                 to_size,
                 b,
                 bl,
                 add,
                 add_generic,
                 ldr,
                 adrp,
                 str_,
                 str_imm_64,
                 b_blocks,
                 bl_blocks,
                 add_blocks,
                 add_generic_blocks,
                 ldr_blocks,
                 adrp_blocks,
                 str_blocks,
                 str_imm_64_blocks):
        super().__init__(ffrom, to_size)
        self._write_values_to_to(b_blocks, b)
        self._write_values_to_to(bl_blocks, bl)
        self._write_add_values_to_to(add_blocks, add)
        self._write_values_to_to(add_generic_blocks, add_generic)
        self._write_values_to_to(ldr_blocks, ldr)
        self._write_adrp_values_to_to(adrp_blocks, adrp)
        self._write_values_to_to(str_blocks, str_)
        self._write_values_to_to(str_imm_64_blocks, str_imm_64)
        self._fdiff.seek(0)

    def _write_add_values_to_to(self, blocks, from_dict):
        self._write_values_to_to_with_callback(blocks, from_dict, self._pack_add)

    def _write_adrp_values_to_to(self, blocks, from_dict):
        self._write_values_to_to_with_callback(blocks, from_dict, self._pack_adrp)

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


class FromReader(UtilsFromReader):

    def __init__(self,
                 ffrom,
                 b,
                 bl,
                 add,
                 add_generic,
                 ldr,
                 adrp,
                 str_,
                 str_imm_64,
                 b_blocks,
                 bl_blocks,
                 add_blocks,
                 add_generic_blocks,
                 ldr_blocks,
                 adrp_blocks,
                 str_blocks,
                 str_imm_64_blocks):
        super().__init__(ffrom)
        self._write_zeros_to_from(b_blocks, b)
        self._write_zeros_to_from(bl_blocks, bl)
        self._write_zeros_to_from(add_blocks, add)
        self._write_zeros_to_from(add_generic_blocks, add_generic)
        self._write_zeros_to_from(ldr_blocks, ldr)
        self._write_zeros_to_from(adrp_blocks, adrp)
        self._write_zeros_to_from(str_blocks, str_)
        self._write_zeros_to_from(str_imm_64_blocks, str_imm_64)


def disassemble_b(reader, address, b):
    reader.seek(-4, os.SEEK_CUR)
    data = reader.read(4)
    b[address] = struct.unpack('<i', data)[0]


def disassemble_bl(reader, address, bl):
    reader.seek(-4, os.SEEK_CUR)
    data = reader.read(4)
    bl[address] = struct.unpack('<i', data)[0]


def disassemble_add(reader, address, add, add_generic, upper_32):
    rn = ((upper_32 >> 5) & 0x1f)
    rd = (upper_32 & 0x1f)

    if rn == rd:
        shift = ((upper_32 >> 22) & 0x3)
        imm12 = ((upper_32 >> 10) & 0xfff)
        value = imm12
        value |= (shift << 12)
        value |= (rn << 14)
        add[address] = value
    else:
        reader.seek(-4, os.SEEK_CUR)
        data = reader.read(4)
        add_generic[address] = struct.unpack('<i', data)[0]

def disassemble_ldr(reader, address, ldr):
    reader.seek(-4, os.SEEK_CUR)
    data = reader.read(4)
    ldr[address] = struct.unpack('<i', data)[0]


def disassemble_str(reader, address, str_):
    reader.seek(-4, os.SEEK_CUR)
    data = reader.read(4)
    str_[address] = struct.unpack('<i', data)[0]


def disassemble_str_imm_64(reader, address, str_imm_64):
    reader.seek(-4, os.SEEK_CUR)
    data = reader.read(4)
    str_imm_64[address] = struct.unpack('<i', data)[0]


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
    add_generic = {}
    ldr = {}
    str_ = {}
    str_imm_64 = {}
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
            disassemble_add(reader, address, add, add_generic, upper_32)
        elif (upper_32 & 0xff000000) == 0x14000000:
            # disassemble_b(reader, address, b)
            pass
        elif (upper_32 & 0xffc00000) == 0xf9400000:
            disassemble_ldr(reader, address, ldr)
        elif (upper_32 & 0xffc00000) == 0xa9000000:
            disassemble_str(reader, address, str_)
        elif (upper_32 & 0x9f000000) == 0x90000000:
            disassemble_adrp(address, adrp, upper_32)
        elif (upper_32 & 0xffc00000) == 0xb9400000:
            disassemble_ldr(reader, address, ldr)
        elif (upper_32 & 0xffc00000) == 0x39400000:
            # LDRB (immediate) Unsigned offset
            disassemble_ldr(reader, address, ldr)
        elif (upper_32 & 0xffc00000) == 0x39000000:
            # LDRB (immediate) Unsigned offset
            disassemble_ldr(reader, address, ldr)
        elif (upper_32 & 0xffc00000) == 0xb9000000:
            disassemble_str(reader, address, str_)
        elif (upper_32 & 0xffe00000) == 0xf8400000:
            # LDUR 64-bit
            disassemble_ldr(reader, address, ldr)
        elif (upper_32 & 0xffe00000) == 0xb8400000:
            # LDTR 64-bit
            disassemble_ldr(reader, address, ldr)
        elif (upper_32 & 0xffc00000) == 0xf9000000:
            disassemble_str_imm_64(reader, address, str_imm_64)

    return b, bl, add, add_generic, ldr, adrp, str_, str_imm_64


def encode(ffrom, fto):
    ffrom = BytesIO(file_read(ffrom))
    fto = BytesIO(file_read(fto))
    (from_b,
     from_bl,
     from_add,
     from_add_generic,
     from_ldr,
     from_adrp,
     from_str,
     from_str_imm_64) = disassemble(ffrom)
    (to_b,
     to_bl,
     to_add,
     to_add_generic,
     to_ldr,
     to_adrp,
     to_str,
     to_str_imm_64) = disassemble(fto)
    patch = create_patch_block(ffrom, fto, from_b, to_b)
    patch += create_patch_block(ffrom, fto, from_bl, to_bl)
    patch += create_patch_block(ffrom, fto, from_add, to_add)
    patch += create_patch_block(ffrom, fto, from_add_generic, to_add_generic)
    patch += create_patch_block(ffrom, fto, from_ldr, to_ldr)
    patch += create_patch_block(ffrom, fto, from_adrp, to_adrp)
    patch += create_patch_block(ffrom, fto, from_str, to_str)
    patch += create_patch_block(ffrom, fto, from_str_imm_64, to_str_imm_64)

    return ffrom, fto, patch


def create_readers(ffrom, patch, to_size):
    """Return diff and from readers, used when applying a patch.

    """

    fpatch = BytesIO(patch)
    b_blocks = Blocks.from_fpatch(fpatch)
    bl_blocks = Blocks.from_fpatch(fpatch)
    add_blocks = Blocks.from_fpatch(fpatch)
    add_generic_blocks = Blocks.from_fpatch(fpatch)
    ldr_blocks = Blocks.from_fpatch(fpatch)
    adrp_blocks = Blocks.from_fpatch(fpatch)
    str_blocks = Blocks.from_fpatch(fpatch)
    str_imm_64_blocks = Blocks.from_fpatch(fpatch)
    b, bl, add, add_generic, ldr, adrp, str_, str_imm_64 = disassemble(ffrom)
    diff_reader = DiffReader(ffrom,
                             to_size,
                             b,
                             bl,
                             add,
                             add_generic,
                             ldr,
                             adrp,
                             str_,
                             str_imm_64,
                             b_blocks,
                             bl_blocks,
                             add_blocks,
                             add_generic_blocks,
                             ldr_blocks,
                             adrp_blocks,
                             str_blocks,
                             str_imm_64_blocks)
    from_reader = FromReader(ffrom,
                             b,
                             bl,
                             add,
                             add_generic,
                             ldr,
                             adrp,
                             str_,
                             str_imm_64,
                             b_blocks,
                             bl_blocks,
                             add_blocks,
                             add_generic_blocks,
                             ldr_blocks,
                             adrp_blocks,
                             str_blocks,
                             str_imm_64_blocks)

    return diff_reader, from_reader


def info(patch, fsize):
    fpatch = BytesIO(patch)
    b_blocks, b_blocks_size = load_blocks(fpatch)
    bl_blocks, bl_blocks_size = load_blocks(fpatch)
    add_blocks, add_blocks_size = load_blocks(fpatch)
    ldr_blocks, ldr_blocks_size = load_blocks(fpatch)
    adrp_blocks, adrp_blocks_size = load_blocks(fpatch)
    str_blocks, str_blocks_size = load_blocks(fpatch)
    str_imm_64_blocks, str_imm_64_blocks_size = load_blocks(fpatch)
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
        print('Instruction:        str')
        format_blocks(str_blocks, str_blocks_size, fsize)
        print('Instruction:        str (imm 64)')
        format_blocks(str_imm_64_blocks, str_imm_64_blocks_size, fsize)

    return fout.getvalue()
