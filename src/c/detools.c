/**
 * BSD 2-Clause License
 *
 * Copyright (c) 2019, Erik Moqvist
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 *
 * * Redistributions of source code must retain the above copyright
 *   notice, this list of conditions and the following disclaimer.
 *
 * * Redistributions in binary form must reproduce the above copyright
 *   notice, this list of conditions and the following disclaimer in
 *   the documentation and/or other materials provided with the
 *   distribution.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
 * FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
 * COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
 * INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
 * (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 * SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
 * HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
 * STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
 * OF THE POSSIBILITY OF SUCH DAMAGE.
 */

#include <stdlib.h>
#include "detools.h"

/* Patch types. */
#define PATCH_TYPE_NORMAL                                   0
#define PATCH_TYPE_IN_PLACE                                 1

/* Compressions. */
#define COMPRESSION_NONE                                    0
#define COMPRESSION_LZMA                                    1
#define COMPRESSION_CRLE                                    2

/* Apply patch states. */
#define STATE_INIT                                          0
#define STATE_DIFF_SIZE                                     1
#define STATE_DIFF_DATA                                     2
#define STATE_EXTRA_SIZE                                    3
#define STATE_EXTRA_DATA                                    4
#define STATE_ADJUSTMENT                                    5
#define STATE_DONE                                          6

/* Size states. */
#define SIZE_STATE_FIRST                                    0
#define SIZE_STATE_CONSECUTIVE                              1

#define MIN(x, y) (((x) < (y)) ? (x) : (y))

/*
 * Utility functions.
 */

static size_t chunk_left(struct detools_apply_patch_chunk_t *self_p)
{
    return (self_p->size - self_p->offset);
}

static bool chunk_available(struct detools_apply_patch_chunk_t *self_p)
{
    return (chunk_left(self_p) > 0);
}

static uint8_t chunk_get_no_check(struct detools_apply_patch_chunk_t *self_p)
{
    uint8_t data;

    data = self_p->buf_p[self_p->offset];
    self_p->offset++;

    return (data);
}

static int chunk_get(struct detools_apply_patch_chunk_t *self_p,
                     uint8_t *data_p)
{
    if (!chunk_available(self_p)) {
        return (1);
    }

    *data_p = chunk_get_no_check(self_p);

    return (0);
}

static void chunk_read_all_no_check(struct detools_apply_patch_chunk_t *self_p,
                                    uint8_t *buf_p,
                                    size_t size)
{
    memcpy(buf_p, &self_p->buf_p[self_p->offset], size);
    self_p->offset += size;
}

static int chunk_read(struct detools_apply_patch_chunk_t *self_p,
                      uint8_t *buf_p,
                      size_t *size_p)
{
    if (!chunk_available(self_p)) {
        return (1);
    }

    *size_p = MIN(*size_p, chunk_left(self_p));
    chunk_read_all_no_check(self_p, buf_p, *size_p);

    return (0);
}

static void unpack_unsigned_size_init(
    struct detools_unpack_unsigned_size_t *self_p)
{
    self_p->state = SIZE_STATE_FIRST;
    self_p->value = 0;
    self_p->offset = 0;
}

static int unpack_unsigned_size(struct detools_unpack_unsigned_size_t *self_p,
                                struct detools_apply_patch_t *apply_patch_p,
                                int *size_p)
{
    int res;
    uint8_t byte;

    do {
        switch (self_p->state) {

        case SIZE_STATE_FIRST:
            res = chunk_get(&apply_patch_p->chunk, &byte);

            if (res != 0) {
                return (res);
            }

            self_p->value = (byte & 0x7f);
            self_p->offset = 7;
            self_p->state = SIZE_STATE_CONSECUTIVE;
            break;

        case SIZE_STATE_CONSECUTIVE:
            res = chunk_get(&apply_patch_p->chunk, &byte);

            if (res != 0) {
                return (res);
            }

            self_p->value |= ((byte & 0x7f) << self_p->offset);
            self_p->offset += 7;
            break;

        default:
            return (-DETOOLS_INTERNAL_ERROR);
        }
    } while ((byte & 0x80) != 0);

    *size_p = self_p->value;

    return (0);
}

static int unpack_header_size(struct detools_apply_patch_t *self_p, int *size_p)
{
    uint8_t byte;
    int offset;
    int res;

    res = chunk_get(&self_p->chunk, &byte);

    if (res != 0) {
        return (-DETOOLS_SHORT_HEADER);
    }

    *size_p = (byte & 0x3f);
    offset = 6;

    while ((byte & 0x80) != 0) {
        res = chunk_get(&self_p->chunk, &byte);

        if (res != 0) {
            return (-DETOOLS_SHORT_HEADER);
        }

        *size_p |= ((byte & 0x7f) << offset);
        offset += 7;
    }

    return (0);
}

/*
 * None patch reader.
 */

#if DETOOLS_CONFIG_COMPRESSION_NONE == 1

static int patch_reader_none_decompress(
    struct detools_apply_patch_patch_reader_t *self_p,
    uint8_t *buf_p,
    size_t *size_p)
{
    int res;
    struct detools_apply_patch_patch_reader_none_t *none_p;

    none_p = &self_p->compression.none;

    if (none_p->patch_offset + *size_p > none_p->patch_size) {
        return (-DETOOLS_CORRUPT_PATCH);
    }

    res = chunk_read(&self_p->apply_patch_p->chunk,
                     buf_p,
                     size_p);

    if (res != 0) {
        return (res);
    }

    none_p->patch_offset += *size_p;

    return (0);
}

static int patch_reader_none_destroy(
    struct detools_apply_patch_patch_reader_t *self_p)
{
    struct detools_apply_patch_patch_reader_none_t *none_p;

    none_p = &self_p->compression.none;

    if (none_p->patch_offset == none_p->patch_size) {
        return (0);
    } else {
        return (-DETOOLS_CORRUPT_PATCH);
    }
}

static int patch_reader_none_init(struct detools_apply_patch_patch_reader_t *self_p,
                                  size_t patch_size)
{
    struct detools_apply_patch_patch_reader_none_t *none_p;

    none_p = &self_p->compression.none;
    none_p->patch_size = patch_size;
    none_p->patch_offset = 0;
    self_p->destroy = patch_reader_none_destroy;
    self_p->decompress = patch_reader_none_decompress;

    return (0);
}

#endif

/*
 * LZMA patch reader.
 */

#if DETOOLS_CONFIG_COMPRESSION_LZMA == 1

static int get_decompressed_data(
    struct detools_apply_patch_patch_reader_lzma_t *lzma_p,
    uint8_t *buf_p,
    size_t size)
{
    int res;

    if (lzma_p->output_size >= size) {
        memcpy(buf_p, lzma_p->output_p, size);
        memmove(lzma_p->output_p,
                &lzma_p->output_p[size],
                lzma_p->output_size - size);
        lzma_p->output_size -= size;
        res = 0;
    } else {
        res = 1;
    }

    return (res);
}

static int prepare_input_buffer(struct detools_apply_patch_patch_reader_t *self_p)
{
    struct detools_apply_patch_patch_reader_lzma_t *lzma_p;
    uint8_t *next_p;
    size_t left;

    lzma_p = &self_p->compression.lzma;
    left = chunk_left(&self_p->apply_patch_p->chunk);

    if (left == 0) {
        return (1);
    }

    next_p = malloc(lzma_p->stream.avail_in + left);

    if (next_p == NULL) {
        return (-DETOOLS_OUT_OF_MEMORY);
    }

    if (lzma_p->stream.next_in != NULL) {
        memcpy(next_p, lzma_p->stream.next_in, lzma_p->stream.avail_in);
        free(lzma_p->input_p);
    }

    lzma_p->input_p = next_p;
    chunk_read_all_no_check(&self_p->apply_patch_p->chunk,
                            &lzma_p->input_p[lzma_p->stream.avail_in],
                            left);
    lzma_p->stream.next_in = next_p;
    lzma_p->stream.avail_in += left;

    return (0);
}

static int prepare_output_buffer(struct detools_apply_patch_patch_reader_t *self_p,
                                 size_t size)
{
    struct detools_apply_patch_patch_reader_lzma_t *lzma_p;
    uint8_t *output_p;

    lzma_p = &self_p->compression.lzma;

    output_p = malloc(size);

    if (output_p == NULL) {
        return (-DETOOLS_OUT_OF_MEMORY);
    }

    if (lzma_p->output_p != NULL) {
        memcpy(output_p, lzma_p->output_p, lzma_p->output_size);
        free(lzma_p->output_p);
    }

    lzma_p->output_p = output_p;
    lzma_p->stream.next_out = (output_p + lzma_p->output_size);
    lzma_p->stream.avail_out = (size - lzma_p->output_size);

    return (0);
}

static int patch_reader_lzma_decompress(
    struct detools_apply_patch_patch_reader_t *self_p,
    uint8_t *buf_p,
    size_t *size_p)
{
    int res;
    struct detools_apply_patch_patch_reader_lzma_t *lzma_p;
    lzma_ret ret;

    lzma_p = &self_p->compression.lzma;

    /* Check if enough decompressed data is available. */
    res = get_decompressed_data(lzma_p, buf_p, *size_p);

    if (res == 0) {
        return (res);
    }

    while (1) {
        /* Try to decompress requested data. */
        if (lzma_p->stream.avail_in > 0) {
            res = prepare_output_buffer(self_p, *size_p);

            if (res != 0) {
                return (res);
            }

            ret = lzma_code(&lzma_p->stream, LZMA_RUN);

            switch (ret) {

            case LZMA_OK:
            case LZMA_STREAM_END:
                break;

            default:
                return (-DETOOLS_LZMA_DECODE);
            }

            lzma_p->output_size = (size_t)(lzma_p->stream.next_out - lzma_p->output_p);
        }

        /* Check if enough decompressed data is available. */
        res = get_decompressed_data(lzma_p, buf_p, *size_p);

        if (res == 0) {
            return (res);
        }

        /* Get more data to decompress. */
        res = prepare_input_buffer(self_p);

        if (res != 0) {
            return (res);
        }
    }
}

static int patch_reader_lzma_destroy(
    struct detools_apply_patch_patch_reader_t *self_p)
{
    struct detools_apply_patch_patch_reader_lzma_t *lzma_p;

    lzma_p = &self_p->compression.lzma;

    if (lzma_p->input_p != NULL) {
        free(lzma_p->input_p);
    }

    if (lzma_p->output_p != NULL) {
        free(lzma_p->output_p);
    }

    lzma_end(&lzma_p->stream);

    if ((lzma_p->stream.avail_in == 0) && (lzma_p->output_size == 0)) {
        return (0);
    } else {
        return (-DETOOLS_CORRUPT_PATCH);
    }
}

static int patch_reader_lzma_init(struct detools_apply_patch_patch_reader_t *self_p)
{
    lzma_ret ret;
    struct detools_apply_patch_patch_reader_lzma_t *lzma_p;

    lzma_p = &self_p->compression.lzma;
    memset(&lzma_p->stream, 0, sizeof(lzma_p->stream));

    ret = lzma_alone_decoder(&lzma_p->stream, UINT64_MAX);

    if (ret != LZMA_OK) {
        return (-DETOOLS_LZMA_INIT);
    }

    lzma_p->input_p = NULL;
    lzma_p->output_p = NULL;
    lzma_p->output_size = 0;
    self_p->destroy = patch_reader_lzma_destroy;
    self_p->decompress = patch_reader_lzma_decompress;

    return (0);
}

#endif

/*
 * CRLE patch reader.
 */

#if DETOOLS_CONFIG_COMPRESSION_CRLE == 1

static int patch_reader_crle_decompress_idle(
    struct detools_apply_patch_patch_reader_t *self_p,
    struct detools_apply_patch_patch_reader_crle_t *crle_p)
{
    int res;
    uint8_t kind;

    res = chunk_get(&self_p->apply_patch_p->chunk, &kind);

    if (res != 0) {
        return (res);
    }

    res = 2;

    switch (kind) {

    case 0:
        crle_p->state = DETOOLS_CRLE_STATE_SCATTERED_SIZE;
        unpack_unsigned_size_init(&crle_p->kind.scattered.size);
        break;

    case 1:
        crle_p->state = DETOOLS_CRLE_STATE_REPEATED_REPETITIONS;
        unpack_unsigned_size_init(&crle_p->kind.repeated.size);
        break;

    default:
        res = -DETOOLS_CORRUPT_PATCH;
        break;
    }

    return (res);
}

static int patch_reader_crle_decompress_scattered_size(
    struct detools_apply_patch_patch_reader_t *self_p,
    struct detools_apply_patch_patch_reader_crle_t *crle_p)
{
    int res;
    int size;

    res = unpack_unsigned_size(&crle_p->kind.scattered.size,
                               self_p->apply_patch_p,
                               &size);

    if (res != 0) {
        return (res);
    }

    crle_p->state = DETOOLS_CRLE_STATE_SCATTERED_DATA;
    crle_p->kind.scattered.number_of_bytes_left = (size_t)size;

    return (2);
}

static int patch_reader_crle_decompress_scattered_data(
    struct detools_apply_patch_patch_reader_t *self_p,
    struct detools_apply_patch_patch_reader_crle_t *crle_p,
    uint8_t *buf_p,
    size_t *size_p)
{
    int res;

    *size_p = MIN(*size_p, crle_p->kind.scattered.number_of_bytes_left);

    res = chunk_read(&self_p->apply_patch_p->chunk, buf_p, size_p);

    if (res != 0) {
        return (res);
    }

    crle_p->kind.scattered.number_of_bytes_left -= *size_p;

    if (crle_p->kind.scattered.number_of_bytes_left == 0) {
        crle_p->state = DETOOLS_CRLE_STATE_IDLE;
    }

    return (0);
}

static int patch_reader_crle_decompress_repeated_repetitions(
    struct detools_apply_patch_patch_reader_t *self_p,
    struct detools_apply_patch_patch_reader_crle_t *crle_p)
{
    int res;
    int repetitions;

    res = unpack_unsigned_size(&crle_p->kind.repeated.size,
                               self_p->apply_patch_p,
                               &repetitions);

    if (res != 0) {
        return (res);
    }

    crle_p->state = DETOOLS_CRLE_STATE_REPEATED_DATA;
    crle_p->kind.repeated.number_of_bytes_left = (size_t)repetitions;

    return (2);
}

static int patch_reader_crle_decompress_repeated_data(
    struct detools_apply_patch_patch_reader_t *self_p,
    struct detools_apply_patch_patch_reader_crle_t *crle_p)
{
    int res;

    res = chunk_get(&self_p->apply_patch_p->chunk,
                    &crle_p->kind.repeated.value);

    if (res != 0) {
        return (res);
    }

    crle_p->state = DETOOLS_CRLE_STATE_REPEATED_DATA_READ;

    return (2);
}

static int patch_reader_crle_decompress_repeated_data_read(
    struct detools_apply_patch_patch_reader_crle_t *crle_p,
    uint8_t *buf_p,
    size_t *size_p)
{
    size_t size;
    size_t i;

    size = MIN(*size_p, crle_p->kind.repeated.number_of_bytes_left);

    for (i = 0; i < size; i++) {
        buf_p[i] = crle_p->kind.repeated.value;
    }

    *size_p = size;
    crle_p->kind.repeated.number_of_bytes_left -= size;

    if (crle_p->kind.repeated.number_of_bytes_left == 0) {
        crle_p->state = DETOOLS_CRLE_STATE_IDLE;
    }

    return (0);
}

static int patch_reader_crle_decompress(
    struct detools_apply_patch_patch_reader_t *self_p,
    uint8_t *buf_p,
    size_t *size_p)
{
    int res;
    struct detools_apply_patch_patch_reader_crle_t *crle_p;

    crle_p = &self_p->compression.crle;

    do {
        switch (crle_p->state) {

        case DETOOLS_CRLE_STATE_IDLE:
            res = patch_reader_crle_decompress_idle(self_p, crle_p);
            break;

        case DETOOLS_CRLE_STATE_SCATTERED_SIZE:
            res = patch_reader_crle_decompress_scattered_size(self_p, crle_p);
            break;

        case DETOOLS_CRLE_STATE_SCATTERED_DATA:
            res = patch_reader_crle_decompress_scattered_data(self_p,
                                                              crle_p,
                                                              buf_p,
                                                              size_p);
            break;

        case DETOOLS_CRLE_STATE_REPEATED_REPETITIONS:
            res = patch_reader_crle_decompress_repeated_repetitions(self_p,
                                                                    crle_p);
            break;

        case DETOOLS_CRLE_STATE_REPEATED_DATA:
            res = patch_reader_crle_decompress_repeated_data(self_p, crle_p);
            break;

        case DETOOLS_CRLE_STATE_REPEATED_DATA_READ:
            res = patch_reader_crle_decompress_repeated_data_read(crle_p,
                                                                  buf_p,
                                                                  size_p);
            break;

        default:
            res = -DETOOLS_INTERNAL_ERROR;
            break;
        }
    } while (res == 2);

    return (res);
}

static int patch_reader_crle_destroy(
    struct detools_apply_patch_patch_reader_t *self_p)
{
    (void)self_p;

    return (0);
}

static int patch_reader_crle_init(struct detools_apply_patch_patch_reader_t *self_p)
{

    struct detools_apply_patch_patch_reader_crle_t *crle_p;

    crle_p = &self_p->compression.crle;
    crle_p->state = DETOOLS_CRLE_STATE_IDLE;
    self_p->destroy = patch_reader_crle_destroy;
    self_p->decompress = patch_reader_crle_decompress;

    return (0);
}

#endif

/*
 * Patch reader.
 */

/**
 * Initialize given patch reader.
 */
static int patch_reader_init(struct detools_apply_patch_patch_reader_t *self_p,
                             struct detools_apply_patch_t *apply_patch_p,
                             size_t patch_size,
                             int compression)
{
    int res;

#if DETOOLS_CONFIG_COMPRESSION_NONE != 1
    (void)patch_size;
#endif

    self_p->apply_patch_p = apply_patch_p;
    self_p->size.state = SIZE_STATE_FIRST;

    switch (compression) {

#if DETOOLS_CONFIG_COMPRESSION_NONE == 1
    case COMPRESSION_NONE:
        res = patch_reader_none_init(self_p, patch_size);
        break;
#endif

#if DETOOLS_CONFIG_COMPRESSION_LZMA == 1
    case COMPRESSION_LZMA:
        res = patch_reader_lzma_init(self_p);
        break;
#endif

#if DETOOLS_CONFIG_COMPRESSION_CRLE == 1
    case COMPRESSION_CRLE:
        res = patch_reader_crle_init(self_p);
        break;
#endif

    default:
        res = -DETOOLS_BAD_COMPRESSION;
        break;
    }

    return (res);
}

/**
 * Try to decompress given number of bytes.
 *
 * @return zero(0) if at least one byte was decompressed, one(1) if
 *         zero bytes were decompressed and more input is needed, or
 *         negative error code.
 */
static int patch_reader_decompress(
    struct detools_apply_patch_patch_reader_t *self_p,
    uint8_t *buf_p,
    size_t *size_p)
{
    return (self_p->decompress(self_p, buf_p, size_p));
}

/**
 * Unpack a size value.
 */
static int patch_reader_unpack_size(
    struct detools_apply_patch_patch_reader_t *self_p,
    int *size_p)
{
    int res;
    uint8_t byte;
    size_t size;

    size = 1;

    do {
        switch (self_p->size.state) {

        case SIZE_STATE_FIRST:
            res = patch_reader_decompress(self_p, &byte, &size);

            if (res != 0) {
                return (res);
            }

            self_p->size.is_signed = ((byte & 0x40) == 0x40);
            self_p->size.value = (byte & 0x3f);
            self_p->size.offset = 6;
            self_p->size.state = SIZE_STATE_CONSECUTIVE;

            break;

        case SIZE_STATE_CONSECUTIVE:
            res = patch_reader_decompress(self_p, &byte, &size);

            if (res != 0) {
                return (res);
            }

            self_p->size.value |= ((byte & 0x7f) << self_p->size.offset);
            self_p->size.offset += 7;

            break;

        default:
            return (-DETOOLS_INTERNAL_ERROR);
        }

        if ((byte & 0x80) == 0) {
            self_p->size.state = SIZE_STATE_FIRST;

            if (self_p->size.is_signed) {
                self_p->size.value *= -1;
            }

            *size_p = self_p->size.value;
        }
    } while ((byte & 0x80) != 0);

    return (res);
}

static int process_init(struct detools_apply_patch_t *self_p)
{
    int patch_type;
    int compression;
    uint8_t byte;
    int res;
    int to_size;

    if (chunk_get(&self_p->chunk, &byte) != 0) {
        return (-DETOOLS_SHORT_HEADER);
    }

    patch_type = ((byte >> 4) & 0x7);
    compression = (byte & 0xf);

    if (patch_type != PATCH_TYPE_NORMAL) {
        return (-DETOOLS_BAD_PATCH_TYPE);
    }


    res = unpack_header_size(self_p, &to_size);

    if (res != 0) {
        return (res);
    }

    res = patch_reader_init(&self_p->patch_reader,
                            self_p,
                            self_p->patch_size - self_p->chunk.offset,
                            compression);

    if (res != 0) {
        return (res);
    }

    if (to_size < 0) {
        return (-DETOOLS_CORRUPT_PATCH);
    }

    self_p->to_pos = 0;
    self_p->to_size = (size_t)to_size;

    if (to_size > 0) {
        self_p->state = STATE_DIFF_SIZE;
    } else {
        self_p->state = STATE_DONE;
    }

    return (res);
}

static int process_size(struct detools_apply_patch_t *self_p,
                        int next_state)
{
    int res;
    int size;

    res = patch_reader_unpack_size(&self_p->patch_reader, &size);

    if (res != 0) {
        return (res);
    }

    if (self_p->to_pos + (size_t)size > self_p->to_size) {
        return (-DETOOLS_CORRUPT_PATCH);
    }

    self_p->state = next_state;
    self_p->chunk_size = (size_t)size;

    return (res);
}

static int process_data(struct detools_apply_patch_t *self_p,
                        int next_state)
{
    int res;
    size_t i;
    uint8_t to[128];
    size_t to_size;
    uint8_t from[128];

    to_size = MIN(sizeof(to), self_p->chunk_size);

    if (to_size == 0) {
        self_p->state = next_state;

        return (0);
    }

    res = patch_reader_decompress(&self_p->patch_reader,
                                  &to[0],
                                  &to_size);

    if (res != 0) {
        return (res);
    }

    if (next_state == STATE_EXTRA_SIZE) {
        res = self_p->from_read(self_p->arg_p, &from[0], to_size);

        if (res != 0) {
            return (-DETOOLS_IO_FAILED);
        }

        for (i = 0; i < to_size; i++) {
            to[i] = (uint8_t)(to[i] + from[i]);
        }
    }

    self_p->to_pos += to_size;
    self_p->chunk_size -= to_size;

    res = self_p->to_write(self_p->arg_p, &to[0], to_size);

    if (res != 0) {
        return (-DETOOLS_IO_FAILED);
    }

    return (res);
}

static int process_diff_size(struct detools_apply_patch_t *self_p)
{
    return (process_size(self_p, STATE_DIFF_DATA));
}

static int process_diff_data(struct detools_apply_patch_t *self_p)
{
    return (process_data(self_p, STATE_EXTRA_SIZE));
}

static int process_extra_size(struct detools_apply_patch_t *self_p)
{
    return (process_size(self_p, STATE_EXTRA_DATA));
}

static int process_extra_data(struct detools_apply_patch_t *self_p)
{
    return (process_data(self_p, STATE_ADJUSTMENT));
}

static int process_adjustment(struct detools_apply_patch_t *self_p)
{
    int res;
    int offset;

    res = patch_reader_unpack_size(&self_p->patch_reader, &offset);

    if (res != 0) {
        return (res);
    }

    res = self_p->from_seek(self_p->arg_p, offset);

    if (res != 0) {
        return (-DETOOLS_IO_FAILED);
    }

    if (self_p->to_pos == self_p->to_size) {
        self_p->state = STATE_DONE;
    } else {
        self_p->state = STATE_DIFF_SIZE;
    }

    return (res);
}

static int apply_patch_process_once(struct detools_apply_patch_t *self_p)
{
    int res;

    switch (self_p->state) {

    case STATE_INIT:
        res = process_init(self_p);
        break;

    case STATE_DIFF_SIZE:
        res = process_diff_size(self_p);
        break;

    case STATE_DIFF_DATA:
        res = process_diff_data(self_p);
        break;

    case STATE_EXTRA_SIZE:
        res = process_extra_size(self_p);
        break;

    case STATE_EXTRA_DATA:
        res = process_extra_data(self_p);
        break;

    case STATE_ADJUSTMENT:
        res = process_adjustment(self_p);
        break;

    case STATE_DONE:
        res = -DETOOLS_ALREADY_DONE;
        break;

    default:
        res = -DETOOLS_INTERNAL_ERROR;
        break;
    }

    return (res);
}

static int apply_patch_common_finalize(
    int res,
    struct detools_apply_patch_patch_reader_t *patch_reader_p,
    size_t to_size)
{
    if (res == 1) {
        res = -DETOOLS_NOT_ENOUGH_PATCH_DATA;
    }

    if (res == -DETOOLS_ALREADY_DONE) {
        res = 0;
    }

    if (patch_reader_p->destroy != NULL) {
        if (res == 0) {
            res = patch_reader_p->destroy(patch_reader_p);
        } else {
            (void)patch_reader_p->destroy(patch_reader_p);
        }
    }

    if (res == 0) {
        res = (int)to_size;
    }

    return (res);
}

int detools_apply_patch_init(struct detools_apply_patch_t *self_p,
                             detools_read_t from_read,
                             detools_seek_t from_seek,
                             size_t patch_size,
                             detools_write_t to_write,
                             void *arg_p)
{
    self_p->from_read = from_read;
    self_p->from_seek = from_seek;
    self_p->patch_size = patch_size;
    self_p->to_write = to_write;
    self_p->arg_p = arg_p;
    self_p->state = STATE_INIT;
    self_p->patch_reader.destroy = NULL;

    return (0);
}

int detools_apply_patch_process(struct detools_apply_patch_t *self_p,
                                const uint8_t *patch_p,
                                size_t size)
{
    int res;

    res = 0;
    self_p->chunk.buf_p = patch_p;
    self_p->chunk.size = size;
    self_p->chunk.offset = 0;

    while (chunk_available(&self_p->chunk) && (res >= 0)) {
        res = apply_patch_process_once(self_p);
    }

    if (res == 1) {
        res = 0;
    }

    return (res);
}

int detools_apply_patch_finalize(struct detools_apply_patch_t *self_p)
{
    int res;

    self_p->chunk.size = 0;
    self_p->chunk.offset = 0;

    do {
        res = apply_patch_process_once(self_p);
    } while (res == 0);

    return (apply_patch_common_finalize(res,
                                        &self_p->patch_reader,
                                        self_p->to_size));
}

static int apply_patch_in_place_process_once(
    struct detools_apply_patch_in_place_t *self_p)
{
    (void)self_p;

    int res;

    res = -DETOOLS_NOT_IMPLEMENTED;

    return (res);
}

int detools_apply_patch_in_place_init(
    struct detools_apply_patch_in_place_t *self_p,
    detools_mem_read_t mem_read,
    detools_mem_write_t mem_write,
    detools_mem_erase_t mem_erase,
    size_t patch_size,
    void *arg_p)
{
    self_p->mem_read = mem_read;
    self_p->mem_write = mem_write;
    self_p->mem_erase = mem_erase;
    self_p->patch_size = patch_size;
    self_p->arg_p = arg_p;
    self_p->state = STATE_INIT;
    self_p->patch_reader.destroy = NULL;

    return (0);
}

int detools_apply_patch_in_place_process(
    struct detools_apply_patch_in_place_t *self_p,
    const uint8_t *patch_p,
    size_t size)
{
    int res;

    res = 0;
    self_p->chunk.buf_p = patch_p;
    self_p->chunk.size = size;
    self_p->chunk.offset = 0;

    while (chunk_available(&self_p->chunk) && (res >= 0)) {
        res = apply_patch_in_place_process_once(self_p);
    }

    if (res == 1) {
        res = 0;
    }

    return (res);
}

int detools_apply_patch_in_place_finalize(
    struct detools_apply_patch_in_place_t *self_p)
{
    int res;

    self_p->chunk.size = 0;
    self_p->chunk.offset = 0;

    do {
        res = apply_patch_in_place_process_once(self_p);
    } while (res == 0);

    return (apply_patch_common_finalize(res,
                                        &self_p->patch_reader,
                                        self_p->to_size));
}

/*
 * Callback functionality.
 */

static int callbacks_process(struct detools_apply_patch_t *apply_patch_p,
                             detools_read_t patch_read,
                             size_t patch_size,
                             void *arg_p)
{
    int res;
    size_t patch_offset;
    size_t chunk_size;
    uint8_t chunk[512];

    res = 0;
    patch_offset = 0;

    while ((patch_offset < patch_size) && (res == 0)) {
        chunk_size = MIN(patch_size - patch_offset, 512);
        res = patch_read(arg_p, &chunk[0], chunk_size);

        if (res == 0) {
            res = detools_apply_patch_process(apply_patch_p,
                                              &chunk[0],
                                              chunk_size);
            patch_offset += chunk_size;
        } else {
            res = -DETOOLS_IO_FAILED;
        }
    }

    if (res == 0) {
        res = detools_apply_patch_finalize(apply_patch_p);
    } else {
        (void)detools_apply_patch_finalize(apply_patch_p);
    }

    return (res);
}

int detools_apply_patch_callbacks(detools_read_t from_read,
                                  detools_seek_t from_seek,
                                  detools_read_t patch_read,
                                  size_t patch_size,
                                  detools_write_t to_write,
                                  void *arg_p)
{
    int res;
    struct detools_apply_patch_t apply_patch;

    res = detools_apply_patch_init(&apply_patch,
                                   from_read,
                                   from_seek,
                                   patch_size,
                                   to_write,
                                   arg_p);

    if (res != 0) {
        return (res);
    }

    return (callbacks_process(&apply_patch, patch_read, patch_size, arg_p));
}

static int in_place_callbacks_process(
    struct detools_apply_patch_in_place_t *apply_patch_p,
    detools_read_t patch_read,
    size_t patch_size,
    void *arg_p)
{
    int res;
    size_t patch_offset;
    size_t chunk_size;
    uint8_t chunk[512];

    res = 0;
    patch_offset = 0;

    while ((patch_offset < patch_size) && (res == 0)) {
        chunk_size = MIN(patch_size - patch_offset, 512);
        res = patch_read(arg_p, &chunk[0], chunk_size);

        if (res == 0) {
            res = detools_apply_patch_in_place_process(apply_patch_p,
                                                       &chunk[0],
                                                       chunk_size);
            patch_offset += chunk_size;
        } else {
            res = -DETOOLS_IO_FAILED;
        }
    }

    if (res == 0) {
        res = detools_apply_patch_in_place_finalize(apply_patch_p);
    } else {
        (void)detools_apply_patch_in_place_finalize(apply_patch_p);
    }

    return (res);
}

int detools_apply_patch_in_place_callbacks(detools_mem_read_t mem_read,
                                           detools_mem_write_t mem_write,
                                           detools_mem_erase_t mem_erase,
                                           detools_read_t patch_read,
                                           size_t patch_size,
                                           void *arg_p)
{
    int res;
    struct detools_apply_patch_in_place_t apply_patch;

    res = detools_apply_patch_in_place_init(&apply_patch,
                                            mem_read,
                                            mem_write,
                                            mem_erase,
                                            patch_size,
                                            arg_p);

    if (res != 0) {
        return (res);
    }

    return (in_place_callbacks_process(&apply_patch,
                                       patch_read,
                                       patch_size,
                                       arg_p));
}

/*
 * File io functionality.
 */

#if DETOOLS_CONFIG_FILE_IO == 1

struct file_io_t {
    FILE *ffrom_p;
    FILE *fpatch_p;
    FILE *fto_p;
};

static int get_file_size(FILE *file_p, size_t *size_p)
{
    int res;
    long size;

    res = fseek(file_p, 0, SEEK_END);

    if (res != 0) {
        return (-DETOOLS_FILE_SEEK_FAILED);
    }

    size = ftell(file_p);

    if (size <= 0) {
        return (-DETOOLS_FILE_TELL_FAILED);
    }

    *size_p = (size_t)size;

    res = fseek(file_p, 0, SEEK_SET);

    if (res != 0) {
        return (-DETOOLS_FILE_SEEK_FAILED);
    }

    return (res);
}

static int file_io_init(struct file_io_t *self_p,
                        const char *from_p,
                        const char *patch_p,
                        const char *to_p,
                        size_t *patch_size_p)
{
    int res;
    FILE *file_p;

    res = -DETOOLS_FILE_OPEN_FAILED;

    /* From. */
    file_p = fopen(from_p, "rb");

    if (file_p == NULL) {
        return (res);
    }

    self_p->ffrom_p = file_p;

    /* To. */
    file_p = fopen(to_p, "wb");

    if (file_p == NULL) {
        goto err1;
    }

    self_p->fto_p = file_p;

    /* Patch. */
    file_p = fopen(patch_p, "rb");

    if (file_p == NULL) {
        goto err2;
    }

    self_p->fpatch_p = file_p;
    res = get_file_size(self_p->fpatch_p, patch_size_p);

    if (res != 0) {
        goto err3;
    }

    return (res);

 err3:
    fclose(self_p->fpatch_p);

 err2:
    fclose(self_p->fto_p);

 err1:
    fclose(self_p->ffrom_p);

    return (res);
}

static int file_io_cleanup(struct file_io_t *self_p)
{
    int res;
    int res2;
    int res3;

    res = fclose(self_p->ffrom_p);
    res2 = fclose(self_p->fto_p);
    res3 = fclose(self_p->fpatch_p);

    if ((res != 0) || (res2 != 0) || (res3 != 0)) {
        res = -DETOOLS_FILE_CLOSE_FAILED;
    }

    return (res);
}

static int file_io_read(FILE *file_p, uint8_t *buf_p, size_t size)
{
    int res;

    res = 0;

    if (size > 0) {
        if (fread(buf_p, size, 1, file_p) != 1) {
            res = -DETOOLS_FILE_READ_FAILED;
        }
    }

    return (res);
}

static int file_io_from_read(void *arg_p, uint8_t *buf_p, size_t size)
{
    struct file_io_t *self_p;

    self_p = (struct file_io_t *)arg_p;

    return (file_io_read(self_p->ffrom_p, buf_p, size));
}

static int file_io_from_seek(void *arg_p, int offset)
{
    struct file_io_t *self_p;

    self_p = (struct file_io_t *)arg_p;

    return (fseek(self_p->ffrom_p, offset, SEEK_CUR));
}

static int file_io_patch_read(void *arg_p, uint8_t *buf_p, size_t size)
{
    struct file_io_t *self_p;

    self_p = (struct file_io_t *)arg_p;

    return (file_io_read(self_p->fpatch_p, buf_p, size));
}

static int file_io_to_write(void *arg_p, const uint8_t *buf_p, size_t size)
{
    int res;
    struct file_io_t *self_p;

    self_p = (struct file_io_t *)arg_p;
    res = 0;

    if (size > 0) {
        if (fwrite(buf_p, size, 1, self_p->fto_p) != 1) {
            res = -DETOOLS_FILE_WRITE_FAILED;
        }
    }

    return (res);
}

int detools_apply_patch_filenames(const char *from_p,
                                  const char *patch_p,
                                  const char *to_p)
{
    int res;
    struct file_io_t file_io;
    size_t patch_size;

    res = file_io_init(&file_io,
                       from_p,
                       patch_p,
                       to_p,
                       &patch_size);

    if (res != 0) {
        return (res);
    }

    res = detools_apply_patch_callbacks(file_io_from_read,
                                        file_io_from_seek,
                                        file_io_patch_read,
                                        patch_size,
                                        file_io_to_write,
                                        &file_io);

    if (res != 0) {
        goto err1;
    }

    return (file_io_cleanup(&file_io));

 err1:
    (void)file_io_cleanup(&file_io);

    return (res);
}

struct in_place_file_io_t {
    FILE *fmemory_p;
    FILE *fpatch_p;
};

static int in_place_file_io_init(struct in_place_file_io_t *self_p,
                                 const char *memory_p,
                                 const char *patch_p,
                                 size_t *patch_size_p)
{
    int res;
    FILE *file_p;

    res = -DETOOLS_FILE_OPEN_FAILED;

    /* Memory. */
    file_p = fopen(memory_p, "r+b");

    if (file_p == NULL) {
        return (res);
    }

    self_p->fmemory_p = file_p;

    /* Patch. */
    file_p = fopen(patch_p, "rb");

    if (file_p == NULL) {
        goto err1;
    }

    self_p->fpatch_p = file_p;
    res = get_file_size(self_p->fpatch_p, patch_size_p);

    if (res != 0) {
        goto err2;
    }

    return (res);

 err2:
    fclose(self_p->fpatch_p);

 err1:
    fclose(self_p->fmemory_p);

    return (res);
}

static int in_place_file_io_mem_read(void *arg_p,
                                     void *dst_p,
                                     uintptr_t src,
                                     size_t size)
{
    int res;
    struct in_place_file_io_t *self_p;

    self_p = (struct in_place_file_io_t *)arg_p;
    res = 0;

    if (size > 0) {
        res = fseek(self_p->fmemory_p, (int)src, SEEK_SET);

        if (res != 0) {
            return (-DETOOLS_FILE_SEEK_FAILED);
        }

        if (fread(dst_p, size, 1, self_p->fmemory_p) != 1) {
            res = -DETOOLS_FILE_READ_FAILED;
        }
    }

    return (res);
}

static int in_place_file_io_mem_write(void *arg_p,
                                      uintptr_t dst,
                                      void *src_p,
                                      size_t size)
{
    int res;
    struct in_place_file_io_t *self_p;

    self_p = (struct in_place_file_io_t *)arg_p;
    res = 0;

    if (size > 0) {
        res = fseek(self_p->fmemory_p, (int)dst, SEEK_SET);

        if (res != 0) {
            return (-DETOOLS_FILE_SEEK_FAILED);
        }

        if (fwrite(src_p, size, 1, self_p->fmemory_p) != 1) {
            res = -DETOOLS_FILE_WRITE_FAILED;
        }
    }

    return (res);
}

static int in_place_file_io_mem_erase(void *arg_p, uintptr_t addr, size_t size)
{
    (void)arg_p;
    (void)addr;
    (void)size;

    return (0);
}

static int in_place_file_io_cleanup(struct in_place_file_io_t *self_p)
{
    int res;
    int res2;

    res = fclose(self_p->fmemory_p);
    res2 = fclose(self_p->fpatch_p);

    if ((res != 0) || (res2 != 0)) {
        res = -DETOOLS_FILE_CLOSE_FAILED;
    }

    return (res);
}

int detools_apply_patch_in_place_filenames(const char *memory_p,
                                           const char *patch_p)
{
    int res;
    struct in_place_file_io_t file_io;
    size_t patch_size;

    res = in_place_file_io_init(&file_io,
                                memory_p,
                                patch_p,
                                &patch_size);

    if (res != 0) {
        return (res);
    }

    res = detools_apply_patch_in_place_callbacks(in_place_file_io_mem_read,
                                                 in_place_file_io_mem_write,
                                                 in_place_file_io_mem_erase,
                                                 file_io_patch_read,
                                                 patch_size,
                                                 &file_io);

    if (res != 0) {
        goto err1;
    }

    return (in_place_file_io_cleanup(&file_io));

 err1:
    (void)in_place_file_io_cleanup(&file_io);

    return (res);
}

#endif

const char *detools_error_as_string(int error)
{
    switch (error) {

    case DETOOLS_NOT_IMPLEMENTED:
        return "Function not implemented.";

    case DETOOLS_NOT_DONE:
        return "Not done.";

    case DETOOLS_BAD_PATCH_TYPE:
        return "Bad patch type.";

    case DETOOLS_BAD_COMPRESSION:
        return "Bad compression.";

    case DETOOLS_INTERNAL_ERROR:
        return "Internal error.";

    case DETOOLS_LZMA_INIT:
        return "LZMA init.";

    case DETOOLS_LZMA_DECODE:
        return "LZMA decode.";

    case DETOOLS_OUT_OF_MEMORY:
        return "Out of memory.";

    case DETOOLS_CORRUPT_PATCH:
        return "Corrupt patch.";

    case DETOOLS_IO_FAILED:
        return "Input/output failed.";

    case DETOOLS_ALREADY_DONE:
        return "Already done.";

    case DETOOLS_FILE_OPEN_FAILED:
        return "File open failed.";

    case DETOOLS_FILE_CLOSE_FAILED:
        return "File close failed.";

    case DETOOLS_FILE_READ_FAILED:
        return "File read failed.";

    case DETOOLS_FILE_WRITE_FAILED:
        return "File write failed.";

    case DETOOLS_FILE_SEEK_FAILED:
        return "File seek failed.";

    case DETOOLS_FILE_TELL_FAILED:
        return "File tell failed.";

    default:
        return "Unknown error.";
    }
}
