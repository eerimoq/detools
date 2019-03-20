from ..errors import Error
from ..common import DATA_FORMAT_ARM_CORTEX_M4
from ..common import format_bad_data_format
from ..common import format_bad_data_format_number
from . import arm


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
    (in the decode function).

    """

    if data_format == 'arm-cortex-m4':
        return arm.cortex_m4_encode(ffrom,
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
    """Return diff and from readers, used when applying a patch.

    """

    if data_format == DATA_FORMAT_ARM_CORTEX_M4:
        return arm.cortex_m4_create_readers(ffrom, patch, to_size)
    else:
        raise Error(format_bad_data_format_number(data_format))


def info(data_format, patch, fsize):
    if data_format == DATA_FORMAT_ARM_CORTEX_M4:
        return arm.cortex_m4_info(patch, fsize)
    else:
        raise Error(format_bad_data_format_number(data_format))
