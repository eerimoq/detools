import logging
import struct
from io import BytesIO
from ..common import file_size
from ..common import file_read
from .utils import create_patch_block_4_bytes as create_patch_block


LOGGER = logging.getLogger(__name__)


def disassemble_64_bl(reader, address, bl, upper_32):
    bl[address] = upper_32


def disassemble_64_add(reader, address, add, upper_32):
    add[address] = upper_32


def disassemble_64_ldr(reader, address, ldr, upper_32):
    ldr[address] = upper_32


def disassemble_64_stp(reader, address, stp, upper_32):
    stp[address] = upper_32


def disassemble_64_adrp(reader, address, adrp, upper_32):
    adrp[address] = upper_32


def disassemble_64(reader):
    """Disassembles given data and returns address-value pairs of b.w, bl,
    *ldr, *ldr.w, data pointers and code pointers.

    """

    length = file_size(reader)
    bl = {}
    add = {}
    ldr = {}
    stp = {}
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
            disassemble_64_bl(reader, address, bl, upper_32)
        elif (upper_32 & 0xff000000) == 0x91000000:
            disassemble_64_add(reader, address, add, upper_32)
        elif (upper_32 & 0xffc00000) == 0xf9400000:
            # LDR (immediate) 64-bit
            disassemble_64_ldr(reader, address, ldr, upper_32)
        elif (upper_32 & 0xffc00000) == 0xa9000000:
            disassemble_64_stp(reader, address, stp, upper_32)
        elif (upper_32 & 0x9f000000) == 0x90000000:
            disassemble_64_adrp(reader, address, adrp, upper_32)
        elif (upper_32 & 0xffc00000) == 0xb9400000:
            # LDR (immediate) 32-bit
            disassemble_64_ldr(reader, address, ldr, upper_32)
        elif (upper_32 & 0xffc00000) == 0x39400000:
            # LDRB (immediate) Unsigned offset
            disassemble_64_ldr(reader, address, ldr, upper_32)
        elif (upper_32 & 0xffc00000) == 0x39000000:
            # LDRB (immediate) Unsigned offset
            disassemble_64_ldr(reader, address, ldr, upper_32)
        elif (upper_32 & 0xffc00000) == 0xb9000000:
            # STR (immediate) 32-bit
            disassemble_64_ldr(reader, address, ldr, upper_32)
        elif (upper_32 & 0xffe00000) == 0xf8400000:
            # LDUR 64-bit
            disassemble_64_ldr(reader, address, ldr, upper_32)
        elif (upper_32 & 0xffe00000) == 0xb8400000:
            # LDTR 64-bit
            disassemble_64_ldr(reader, address, ldr, upper_32)
        elif (upper_32 & 0xffc00000) == 0xf9000000:
            # STR (immediate) 64-bit
            disassemble_64_ldr(reader, address, ldr, upper_32)

    return bl, add, ldr, stp, adrp


def encode(ffrom, fto):
    ffrom = BytesIO(file_read(ffrom))
    fto = BytesIO(file_read(fto))
    from_bl, from_add, from_ldr, from_stp, from_adrp = disassemble_64(ffrom)
    to_bl, to_add, to_ldr, to_stp, to_adrp = disassemble_64(fto)
    patch = create_patch_block(ffrom, fto, from_bl, to_bl)
    patch += create_patch_block(ffrom, fto, from_add, to_add)
    patch += create_patch_block(ffrom, fto, from_ldr, to_ldr)
    patch += create_patch_block(ffrom, fto, from_stp, to_stp)
    patch += create_patch_block(ffrom, fto, from_adrp, to_adrp)

    return ffrom, fto, patch
