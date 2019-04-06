from ..errors import Error
from ..common import DATA_FORMAT_AARCH64
from ..common import DATA_FORMAT_ARM_CORTEX_M4
from ..common import format_bad_data_format
from ..common import format_bad_data_format_number
from . import aarch64
from . import arm_cortex_m4


def encode(ffrom,
           fto,
           data_format,
           from_data_offset,
           from_data_begin,
           from_data_end,
           from_code_begin,
           from_code_end,
           to_data_offset,
           to_data_begin,
           to_data_end,
           to_code_begin,
           to_code_end):
    """Returns the new from-data and to-data, along with a patch that can
    be used to convert the new from-data to the original to-data later
    (by the diff and from readers).

    """

    if data_format == 'aarch64':
        return aarch64.encode(ffrom,
                              fto,
                              from_data_offset,
                              from_data_begin,
                              from_data_end,
                              from_code_begin,
                              from_code_end,
                              to_data_offset,
                              to_data_begin,
                              to_data_end,
                              to_code_begin,
                              to_code_end)
    elif data_format == 'arm-cortex-m4':
        return arm_cortex_m4.encode(ffrom,
                                    fto,
                                    from_data_offset,
                                    from_data_begin,
                                    from_data_end,
                                    from_code_begin,
                                    from_code_end,
                                    to_data_offset,
                                    to_data_begin,
                                    to_data_end,
                                    to_code_begin,
                                    to_code_end)
    else:
        raise Error(format_bad_data_format(data_format))


def create_readers(data_format, ffrom, patch, to_size):
    """Returns diff and from readers, used when applying a patch.

    """

    if data_format == DATA_FORMAT_AARCH64:
        return aarch64.create_readers(ffrom, patch, to_size)
    elif data_format == DATA_FORMAT_ARM_CORTEX_M4:
        return arm_cortex_m4.create_readers(ffrom, patch, to_size)
    else:
        raise Error(format_bad_data_format_number(data_format))


def info(data_format, patch, fsize):
    """Returns an info string.

    """

    if data_format == DATA_FORMAT_AARCH64:
        return aarch64.info(patch, fsize)
    elif data_format == DATA_FORMAT_ARM_CORTEX_M4:
        return arm_cortex_m4.info(patch, fsize)
    else:
        raise Error(format_bad_data_format_number(data_format))
