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
#define PATCH_TYPE_NONE                                    -1
#define PATCH_TYPE_NORMAL                                   0
#define PATCH_TYPE_IN_PLACE                                 1

/* Compressions. */
#define COMPRESSION_NONE                                    0
#define COMPRESSION_LZMA                                    1
#define COMPRESSION_CRLE                                    2

/* Apply patch states. */
#define STATE_DIFF_SIZE                                     0
#define STATE_DIFF_DATA                                     1
#define STATE_EXTRA_SIZE                                    2
#define STATE_EXTRA_DATA                                    3
#define STATE_ADJUSTMENT                                    4
#define STATE_DONE                                          5

/* Size states. */
#define SIZE_STATE_FIRST                                    0
#define SIZE_STATE_CONSECUTIVE                              1

#define MIN(x, y) (((x) < (y)) ? (x) : (y))

/*
 * Utility functions.
 */

static int unpack_size(struct detools_apply_patch_t *self_p, int *size_p)
{
    uint8_t byte;
    bool is_signed;
    int offset;

    if (self_p->chunk.offset == self_p->chunk.size) {
        return (-DETOOLS_SHORT_HEADER);
    }

    byte = self_p->chunk.buf_p[self_p->chunk.offset];
    self_p->chunk.offset++;
    is_signed = ((byte & 0x40) == 0x40);
    *size_p = (byte & 0x3f);
    offset = 6;

    while ((byte & 0x80) != 0) {
        if (self_p->chunk.offset == self_p->chunk.size) {
            return (-DETOOLS_SHORT_HEADER);
        }

        byte = self_p->chunk.buf_p[self_p->chunk.offset];
        self_p->chunk.offset++;
        *size_p |= ((byte & 0x7f) << offset);
        offset += 7;
    }

    if (is_signed) {
        *size_p *= -1;
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
    size_t left;
    struct detools_apply_patch_patch_reader_none_t *none_p;

    none_p = &self_p->compression.none;

    if (none_p->patch_offset + *size_p > none_p->patch_size) {
        return (-DETOOLS_CORRUPT_PATCH);
    }

    left = (self_p->apply_patch_p->chunk.size - self_p->apply_patch_p->chunk.offset);

    if (left == 0) {
        return (1);
    }

    *size_p = MIN(*size_p, left);
    memcpy(buf_p,
           &self_p->apply_patch_p->chunk.buf_p[self_p->apply_patch_p->chunk.offset],
           *size_p);
    self_p->apply_patch_p->chunk.offset += *size_p;
    none_p->patch_offset += *size_p;

    return (0);
}

static int patch_reader_none_init(struct detools_apply_patch_patch_reader_t *self_p,
                                  size_t patch_size)
{
    struct detools_apply_patch_patch_reader_none_t *none_p;

    none_p = &self_p->compression.none;
    none_p->patch_size = patch_size;
    none_p->patch_offset = 0;
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
    left = (self_p->apply_patch_p->chunk.size - self_p->apply_patch_p->chunk.offset);

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
    memcpy(&lzma_p->input_p[lzma_p->stream.avail_in],
           &self_p->apply_patch_p->chunk.buf_p[self_p->apply_patch_p->chunk.offset],
           left);
    lzma_p->stream.next_in = next_p;
    lzma_p->stream.avail_in += left;
    self_p->apply_patch_p->chunk.offset += left;

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
    self_p->decompress = patch_reader_lzma_decompress;

    return (0);
}

#endif

/*
 * CRLE patch reader.
 */

#if DETOOLS_CONFIG_COMPRESSION_CRLE == 1

static int patch_reader_crle_init(struct detools_apply_patch_patch_reader_t *self_p)
{
    (void)self_p;

    return (-DETOOLS_NOT_IMPLEMENTED);
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
 * Decompress exactly given number of bytes.
 *
 * @return zero(0) on success, one(1) if more input is needed, or
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

static int apply_patch_none_init_normal(struct detools_apply_patch_t *self_p,
                                        int compression)
{
    int res;
    int to_size;

    res = unpack_size(self_p, &to_size);

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

    if (to_size <= 0) {
        return (-DETOOLS_CORRUPT_PATCH);
    }

    self_p->patch_type = PATCH_TYPE_NORMAL;
    self_p->to_pos = 0;
    self_p->to_size = (size_t)to_size;
    self_p->state = STATE_DIFF_SIZE;

    return (res);
}

static int apply_patch_none(struct detools_apply_patch_t *self_p)
{
    int res;
    int patch_type;
    int compression;

    if (self_p->chunk.offset == self_p->chunk.size) {
        return (-DETOOLS_SHORT_HEADER);
    }

    patch_type = ((self_p->chunk.buf_p[self_p->chunk.offset] >> 4) & 0x7);
    compression = (self_p->chunk.buf_p[self_p->chunk.offset] & 0xf);
    self_p->chunk.offset++;

    switch (patch_type) {

    case PATCH_TYPE_NORMAL:
        res = apply_patch_none_init_normal(self_p, compression);
        break;

    case PATCH_TYPE_IN_PLACE:
        res = -DETOOLS_NOT_IMPLEMENTED;
        break;

    default:
        res = -DETOOLS_BAD_PATCH_TYPE;
        break;
    }

    return (res);
}

static int process_normal_size(struct detools_apply_patch_t *self_p,
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

static int process_normal_data(struct detools_apply_patch_t *self_p,
                               int next_state)
{
    int res;
    size_t i;
    uint8_t to[128];
    size_t to_size;
    uint8_t from[128];

    to_size = MIN(sizeof(to), self_p->chunk_size);

    res = patch_reader_decompress(&self_p->patch_reader,
                                  &to[0],
                                  &to_size);

    if (res != 0) {
        return (res);
    }

    if (next_state == STATE_EXTRA_SIZE) {
        res = self_p->from_read(self_p->arg_p, &from[0], to_size);

        if (res != 0) {
            return (res);
        }

        for (i = 0; i < to_size; i++) {
            to[i] = (uint8_t)(to[i] + from[i]);
        }
    }

    self_p->to_pos += to_size;
    self_p->chunk_size -= to_size;

    if (self_p->chunk_size == 0) {
        self_p->state = next_state;
    }

    res = self_p->to_write(self_p->arg_p, &to[0], to_size);

    if (res != 0) {
        return (-DETOOLS_IO_FAILED);
    }

    return (res);
}

static int process_normal_diff_size(struct detools_apply_patch_t *self_p)
{
    return (process_normal_size(self_p, STATE_DIFF_DATA));
}

static int process_normal_diff_data(struct detools_apply_patch_t *self_p)
{
    return (process_normal_data(self_p, STATE_EXTRA_SIZE));
}

static int process_normal_extra_size(struct detools_apply_patch_t *self_p)
{
    return (process_normal_size(self_p, STATE_EXTRA_DATA));
}

static int process_normal_extra_data(struct detools_apply_patch_t *self_p)
{
    return (process_normal_data(self_p, STATE_ADJUSTMENT));
}

static int process_normal_adjustment(struct detools_apply_patch_t *self_p)
{
    int res;
    int offset;

    res = patch_reader_unpack_size(&self_p->patch_reader, &offset);

    if (res != 0) {
        return (res);
    }

    res = self_p->from_seek(self_p->arg_p, offset);

    if (res != 0) {
        return (res);
    }

    if (self_p->to_pos == self_p->to_size) {
        self_p->state = STATE_DONE;
    } else {
        self_p->state = STATE_DIFF_SIZE;
    }

    return (res);
}

/**
 * @return Number of consumed patch bytes, or negative error code.
 */
static int apply_patch_normal(struct detools_apply_patch_t *self_p)
{
    int res;

    switch (self_p->state) {

    case STATE_DIFF_SIZE:
        res = process_normal_diff_size(self_p);
        break;

    case STATE_DIFF_DATA:
        res = process_normal_diff_data(self_p);
        break;

    case STATE_EXTRA_SIZE:
        res = process_normal_extra_size(self_p);
        break;

    case STATE_EXTRA_DATA:
        res = process_normal_extra_data(self_p);
        break;

    case STATE_ADJUSTMENT:
        res = process_normal_adjustment(self_p);
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

/**
 * @return Number of consumed patch bytes, or negative error code.
 */
static int apply_patch_in_place(struct detools_apply_patch_t *self_p)
{
    (void)self_p;

    return (-DETOOLS_NOT_IMPLEMENTED);
}

static int apply_patch_process_once(struct detools_apply_patch_t *self_p)
{
    int res;

    switch (self_p->patch_type) {

    case PATCH_TYPE_NONE:
        res = apply_patch_none(self_p);
        break;

    case PATCH_TYPE_NORMAL:
        res = apply_patch_normal(self_p);
        break;

    case PATCH_TYPE_IN_PLACE:
        res = apply_patch_in_place(self_p);
        break;

    default:
        res = -DETOOLS_INTERNAL_ERROR;
        break;
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
    self_p->patch_type = PATCH_TYPE_NONE;

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

    while ((self_p->chunk.offset < self_p->chunk.size) && (res >= 0)) {
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

    res = 0;

    while (res == 0) {
        res = apply_patch_process_once(self_p);
    }

    if (res == -DETOOLS_ALREADY_DONE) {
        res = 0;
    }

    return (res);
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

    while (patch_offset < patch_size) {
        chunk_size = MIN(patch_size - patch_offset, 512);
        res = patch_read(arg_p, &chunk[0], chunk_size);

        if (res != 0) {
            return (-DETOOLS_IO_FAILED);
        }

        res = detools_apply_patch_process(apply_patch_p,
                                          &chunk[0],
                                          chunk_size);

        if (res != 0) {
            return (res);
        }

        patch_offset += chunk_size;
    }

    return (detools_apply_patch_finalize(apply_patch_p));
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
