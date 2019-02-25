# Based on http://zork.net/~st/jottings/sais.html.

S_TYPE = ord("S")
L_TYPE = ord("L")


def build_type_map(data):
    res = bytearray(len(data) + 1)
    res[-1] = S_TYPE

    if not len(data):
        return res

    res[-2] = L_TYPE

    for i in range(len(data) - 2, -1, -1):
        if data[i] > data[i + 1]:
            res[i] = L_TYPE
        elif data[i] == data[i + 1] and res[i + 1] == L_TYPE:
            res[i] = L_TYPE
        else:
            res[i] = S_TYPE

    return res


def is_lms_char(offset, typemap):
    if offset == 0:
        return False

    if typemap[offset] == S_TYPE and typemap[offset - 1] == L_TYPE:
        return True

    return False


def lms_substrings_are_equal(string, typemap, offset_a, offset_b):
    if offset_a == len(string) or offset_b == len(string):
        return False

    i = 0

    while True:
        a_is_lms = is_lms_char(i + offset_a, typemap)
        b_is_lms = is_lms_char(i + offset_b, typemap)

        if i > 0 and a_is_lms and b_is_lms:
            return True

        if a_is_lms != b_is_lms:
            return False

        if string[i + offset_a] != string[i + offset_b]:
            return False

        i += 1


def find_bucket_sizes(string, alphabet_size=256):
    res = [0] * alphabet_size

    for char in string:
        res[char] += 1

    return res


def find_bucket_heads(bucket_sizes):
    offset = 1
    res = []

    for size in bucket_sizes:
        res.append(offset)
        offset += size

    return res


def find_bucket_tails(bucket_sizes):
    offset = 1
    res = []

    for size in bucket_sizes:
        offset += size
        res.append(offset - 1)

    return res


def make_suffix_array_by_induced_sorting(string, alphabet_size):
    typemap = build_type_map(string)
    bucket_sizes = find_bucket_sizes(string, alphabet_size)
    guessed_suffix_array = guess_lms_sort(string, bucket_sizes, typemap)
    induce_sort_l(string, guessed_suffix_array, bucket_sizes, typemap)
    induce_sort_s(string, guessed_suffix_array, bucket_sizes, typemap)
    (summary_string,
     summary_alphabet_size,
     summary_suffix_offsets) = summarise_suffix_array(string,
                                                      guessed_suffix_array,
                                                      typemap)
    summary_suffix_array = make_summary_suffix_array(
        summary_string,
        summary_alphabet_size)
    result = accurate_lms_sort(string,
                               bucket_sizes,
                               summary_suffix_array,
                               summary_suffix_offsets)
    induce_sort_l(string, result, bucket_sizes, typemap)
    induce_sort_s(string, result, bucket_sizes, typemap)

    return result


def guess_lms_sort(string, bucket_sizes, typemap):
    guessed_suffix_array = [-1] * (len(string) + 1)
    bucket_tails = find_bucket_tails(bucket_sizes)

    for i in range(len(string)):
        if not is_lms_char(i, typemap):
            continue

        bucket_index = string[i]
        guessed_suffix_array[bucket_tails[bucket_index]] = i
        bucket_tails[bucket_index] -= 1

    guessed_suffix_array[0] = len(string)

    return guessed_suffix_array


def induce_sort_l(string, guessed_suffix_array, bucket_sizes, typemap):
    bucket_heads = find_bucket_heads(bucket_sizes)

    for i in range(len(guessed_suffix_array)):
        if guessed_suffix_array[i] == -1:
            continue

        j = guessed_suffix_array[i] - 1

        if j < 0:
            continue

        if typemap[j] != L_TYPE:
            continue

        bucket_index = string[j]
        guessed_suffix_array[bucket_heads[bucket_index]] = j
        bucket_heads[bucket_index] += 1


def induce_sort_s(string, guessed_suffix_array, bucket_sizes, typemap):
    bucket_tails = find_bucket_tails(bucket_sizes)

    for i in range(len(guessed_suffix_array)-1, -1, -1):
        j = guessed_suffix_array[i] - 1

        if j < 0:
            continue

        if typemap[j] != S_TYPE:
            continue

        bucket_index = string[j]
        guessed_suffix_array[bucket_tails[bucket_index]] = j
        bucket_tails[bucket_index] -= 1


def summarise_suffix_array(string, guessed_suffix_array, typemap):
    lms_names = [-1] * (len(string) + 1)
    current_name = 0
    last_lms_suffix_offset = None
    lms_names[guessed_suffix_array[0]] = current_name
    last_lms_suffix_offset = guessed_suffix_array[0]

    for i in range(1, len(guessed_suffix_array)):
        suffix_offset = guessed_suffix_array[i]

        if not is_lms_char(suffix_offset, typemap):
            continue

        if not lms_substrings_are_equal(string,
                                        typemap,
                                        last_lms_suffix_offset,
                                        suffix_offset):
            current_name += 1

        last_lms_suffix_offset = suffix_offset
        lms_names[suffix_offset] = current_name

    summary_suffix_offsets = []
    summary_string = []

    for index, name in enumerate(lms_names):
        if name == -1:
            continue

        summary_suffix_offsets.append(index)
        summary_string.append(name)

    summary_alphabet_size = current_name + 1

    return summary_string, summary_alphabet_size, summary_suffix_offsets


def make_summary_suffix_array(summary_string, summary_alphabet_size):
    if summary_alphabet_size == len(summary_string):
        summary_suffix_array = [-1] * (len(summary_string) + 1)
        summary_suffix_array[0] = len(summary_string)

        for x in range(len(summary_string)):
            y = summary_string[x]
            summary_suffix_array[y + 1] = x
    else:
        summary_suffix_array = make_suffix_array_by_induced_sorting(
            summary_string,
            summary_alphabet_size)

    return summary_suffix_array


def accurate_lms_sort(string,
                      bucket_sizes,
                      summary_suffix_array,
                      summary_suffix_offsets):
    suffix_offsets = [-1] * (len(string) + 1)
    bucket_tails = find_bucket_tails(bucket_sizes)

    for i in range(len(summary_suffix_array) - 1, 1, -1):
        string_index = summary_suffix_offsets[summary_suffix_array[i]]
        bucket_index = string[string_index]
        suffix_offsets[bucket_tails[bucket_index]] = string_index
        bucket_tails[bucket_index] -= 1

    suffix_offsets[0] = len(string)

    return suffix_offsets


def sais(data):
    """Calculates the suffix array and returns it as a list.

    """

    return make_suffix_array_by_induced_sorting(data, 256)
