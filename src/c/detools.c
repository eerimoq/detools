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

#include <assert.h>
#include <stdbool.h>
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

#define MIN(x, y) (((x) < (y)) ? (x) : (y))

static int patch_reader_lzma_decompress(
    struct detools_apply_patch_patch_reader_t *self_p,
    uint8_t *buf_p,
    size_t size);

static int unpack_size(const uint8_t *buf_p, size_t size, int *size_p)
{
    uint8_t byte;
    bool is_signed;
    int offset;

    if (size == 0) {
        return (0);
    }

    byte = *buf_p++;
    size--;
    is_signed = ((byte & 0x40) == 0x40);
    *size_p = (byte & 0x3f);
    offset = 6;

    while ((byte & 0x80) != 0) {
        if (size == 0) {
            return (0);
        }

        byte = *buf_p++;
        size--;
        *size_p |= ((byte & 0x7f) << offset);
        offset += 7;
    }

    if (is_signed) {
        *size_p *= -1;
    }

    return ((offset - 6) / 7 + 1);
}

static int patch_reader_none_init(struct detools_apply_patch_patch_reader_t *self_p)
{
    (void)self_p;

    return (-DETOOLS_NOT_IMPLEMENTED);
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

static int patch_reader_crle_init(struct detools_apply_patch_patch_reader_t *self_p)
{
    (void)self_p;

    return (-DETOOLS_NOT_IMPLEMENTED);
}

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

    lzma_p = &self_p->compression.lzma;

    next_p = malloc(lzma_p->stream.avail_in + self_p->chunk.size);

    if (next_p == NULL) {
        return (-DETOOLS_OUT_OF_MEMORY);
    }

    if (lzma_p->stream.next_in != NULL) {
        memcpy(next_p, lzma_p->stream.next_in, lzma_p->stream.avail_in);
        free(lzma_p->input_p);
    }

    lzma_p->input_p = next_p;
    memcpy(&lzma_p->input_p[lzma_p->stream.avail_in],
           self_p->chunk.buf_p,
           self_p->chunk.size);
    lzma_p->stream.next_in = next_p;
    lzma_p->stream.avail_in += self_p->chunk.size;
    self_p->chunk.offset = self_p->chunk.size;

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

/**
 * Decompress exactly given number of bytes.
 *
 * @return zero(0) on success, one(1) if more input is needed, or
 *         negative error code.
 */
static int patch_reader_lzma_decompress(
    struct detools_apply_patch_patch_reader_t *self_p,
    uint8_t *buf_p,
    size_t size)
{
    int res;
    struct detools_apply_patch_patch_reader_lzma_t *lzma_p;
    lzma_ret ret;
    size_t extra_size_out;

    lzma_p = &self_p->compression.lzma;

    /* Check if enough decompressed data is available. */
    res = get_decompressed_data(lzma_p, buf_p, size);

    if (res == 0) {
        return (res);
    }

    /* Decompress more data. */
    res = prepare_input_buffer(self_p);

    if (res != 0) {
        return (res);
    }

    extra_size_out = 1024;

    while (1) {
        res = prepare_output_buffer(self_p, size + extra_size_out);

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

        res = get_decompressed_data(lzma_p, buf_p, size);

        if (res == 0) {
            return (res);
        }

        extra_size_out += 1024;
    }
}

static int patch_reader_init(struct detools_apply_patch_patch_reader_t *self_p,
                              int compression)
{
    int res;

    switch (compression) {

    case COMPRESSION_NONE:
        res = patch_reader_none_init(self_p);
        break;

    case COMPRESSION_LZMA:
        res = patch_reader_lzma_init(self_p);
        break;

    case COMPRESSION_CRLE:
        res = patch_reader_crle_init(self_p);
        break;

    default:
        res = -DETOOLS_BAD_COMPRESSION;
        break;
    }

    return (res);
}

/**
 * Set patch data to be consumed.
 */
static void patch_reader_chunk_set(
    struct detools_apply_patch_patch_reader_t *self_p,
    const uint8_t *buf_p,
    size_t size)
{
    self_p->chunk.buf_p = buf_p;
    self_p->chunk.size = size;
    self_p->chunk.offset = 0;
}

/**
 * @return Number of consumed patch bytes.
 */
static int patch_reader_chunk_offset(
    struct detools_apply_patch_patch_reader_t *self_p)
{
    return ((int)self_p->chunk.offset);
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
    size_t size)
{
    return (self_p->decompress(self_p, buf_p, size));
}

static int patch_reader_unpack_size(
    struct detools_apply_patch_patch_reader_t *self_p,
    int *size_p)
{
    int res;
    uint8_t byte;
    bool is_signed;
    int offset;

    res = patch_reader_decompress(self_p, &byte, 1);

    if (res != 0) {
        return (res);
    }

    is_signed = ((byte & 0x40) == 0x40);
    *size_p = (byte & 0x3f);
    offset = 6;

    while ((byte & 0x80) != 0) {
        res = patch_reader_decompress(self_p, &byte, 1);

        if (res != 0) {
            return (res);
        }

        *size_p |= ((byte & 0x7f) << offset);
        offset += 7;
    }

    if (is_signed) {
        *size_p *= -1;
    }

    return (0);
}

/**
 * @return Number of consumed patch bytes, or negative error code.
 */
static int apply_patch_none(struct detools_apply_patch_t *self_p,
                            const uint8_t *patch_p,
                            size_t size)
{
    int res;
    int patch_type;
    int compression;
    int to_size;

    if (size < 1) {
        return (0);
    }

    patch_type = ((patch_p[0] >> 4) & 0x7);
    compression = (patch_p[0] & 0xf);

    switch (patch_type) {

    case PATCH_TYPE_NORMAL:
        res = patch_reader_init(&self_p->patch_reader, compression);

        if (res != 0) {
            return (res);
        }

        res = unpack_size(&patch_p[1], size - 1, &to_size);

        if (res > 0) {
            if (to_size > 0) {
                self_p->patch_type = patch_type;
                self_p->to_pos = 0;
                self_p->to_size = (size_t)to_size;
                self_p->state = STATE_DIFF_SIZE;
                res++;
            } else {
                res = -DETOOLS_CORRUPT_PATCH;
            }
        }

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

static int apply_patch_in_place(struct detools_apply_patch_t *self_p,
                                const uint8_t *patch_p,
                                size_t size)
{
    (void)self_p;
    (void)patch_p;
    (void)size;

    return (-DETOOLS_NOT_IMPLEMENTED);
}

/**
 * @return Number of consumed patch bytes, or negative error code.
 */
static int process_normal_size(struct detools_apply_patch_t *self_p,
                               int next_state)
{
    int res;
    int size;

    res = patch_reader_unpack_size(&self_p->patch_reader, &size);

    if (res != 0) {
        return (res);
    }

    if (self_p->to_pos + size > self_p->to_size) {
        return (-DETOOLS_CORRUPT_PATCH);
    }

    self_p->state = next_state;
    self_p->chunk_size = size;

    return (res);
}

/**
 * @return Number of consumed patch bytes, or negative error code.
 */
static int process_normal_data(struct detools_apply_patch_t *self_p,
                               int next_state)
{
    int res;
    int i;
    uint8_t to[128];
    size_t to_size;
    uint8_t from[128];

    to_size = MIN(sizeof(to), (size_t)self_p->chunk_size);

    res = patch_reader_decompress(&self_p->patch_reader,
                                  &to[0],
                                  to_size);

    if (res != 0) {
        return (res);
    }

    if (next_state == STATE_EXTRA_SIZE) {
        res = self_p->from_read(self_p->arg_p, &from[0], to_size);

        if (res != 0) {
            return (-DETOOLS_READ_FAILED);
        }

        for (i = 0; i < (int)to_size; i++) {
            to[i] = (uint8_t)(to[i] + from[i]);
        }
    }

    self_p->to_pos += (int)to_size;
    self_p->chunk_size -= (int)to_size;

    if (self_p->chunk_size == 0) {
        self_p->state = next_state;
    }

    res = self_p->to_write(self_p->arg_p, &to[0], to_size);

    if (res != 0) {
        return (-DETOOLS_WRITE_FAILED);
    }

    return (res);
}

/**
 * @return Number of consumed patch bytes, or negative error code.
 */
static int process_normal_diff_size(struct detools_apply_patch_t *self_p)
{
    return (process_normal_size(self_p, STATE_DIFF_DATA));
}

/**
 * @return Number of consumed patch bytes, or negative error code.
 */
static int process_normal_diff_data(struct detools_apply_patch_t *self_p)
{
    return (process_normal_data(self_p, STATE_EXTRA_SIZE));
}

/**
 * @return Number of consumed patch bytes, or negative error code.
 */
static int process_normal_extra_size(struct detools_apply_patch_t *self_p)
{
    return (process_normal_size(self_p, STATE_EXTRA_DATA));
}

/**
 * @return Number of consumed patch bytes, or negative error code.
 */
static int process_normal_extra_data(struct detools_apply_patch_t *self_p)
{
    return (process_normal_data(self_p, STATE_ADJUSTMENT));
}

/**
 * @return Number of consumed patch bytes, or negative error code.
 */
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
        return (-DETOOLS_SEEK_FAILED);
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
static int apply_patch_normal(struct detools_apply_patch_t *self_p,
                              const uint8_t *patch_p,
                              size_t size)
{
    int res;

    patch_reader_chunk_set(&self_p->patch_reader, patch_p, size);

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

    if (res >= 0) {
        res = patch_reader_chunk_offset(&self_p->patch_reader);
    }

    return (res);
}

struct rwer_t {
    FILE *ffrom_p;
    FILE *fto_p;
};

static void *mymalloc(size_t size)
{
    void *buf_p;

    buf_p = malloc(size);
    assert(buf_p != NULL);

    return (buf_p);
}

static FILE *myfopen(const char *name_p, const char *flags_p)
{
    FILE *file_p;

    file_p = fopen(name_p, flags_p);
    assert(file_p != NULL);

    return (file_p);
}

static void rwer_init(struct rwer_t *self_p,
                      const char *from_p,
                      const char *to_p)
{
    self_p->ffrom_p = myfopen(from_p, "rb");
    self_p->fto_p = myfopen(to_p, "wb");
}

static int rwer_read(void *arg_p, uint8_t *buf_p, size_t size)
{
    int res;
    struct rwer_t *self_p;

    self_p = (struct rwer_t *)arg_p;
    res = 0;

    if (size > 0) {
        if (fread(buf_p, size, 1, self_p->ffrom_p) != 1) {
            res = -1;
        }
    }

    return (res);
}

static int rwer_seek(void *arg_p, int offset)
{
    struct rwer_t *self_p;

    self_p = (struct rwer_t *)arg_p;

    return (fseek(self_p->ffrom_p, offset, SEEK_CUR));
}

static int rwer_write(void *arg_p, const uint8_t *buf_p, size_t size)
{
    int res;
    struct rwer_t *self_p;

    self_p = (struct rwer_t *)arg_p;
    res = 0;

    if (size > 0) {
        if (fwrite(buf_p, size, 1, self_p->fto_p) != 1) {
            res = -1;
        }
    }

    return (res);
}

static uint8_t *read_init(const char *name_p, size_t *size_p)
{
    FILE *file_p;
    void *buf_p;
    long size;

    file_p = myfopen(name_p, "rb");

    assert(fseek(file_p, 0, SEEK_END) == 0);
    size = ftell(file_p);
    assert(size > 0);
    *size_p = (size_t)size;
    assert(fseek(file_p, 0, SEEK_SET) == 0);

    buf_p = mymalloc(*size_p);
    assert(fread(buf_p, *size_p, 1, file_p) == 1);

    fclose(file_p);

    return (buf_p);
}

static uint8_t *patch_init(const char *patch_p, size_t *patch_size_p)
{
    return (read_init(patch_p, patch_size_p));
}

int detools_apply_patch_filenames(const char *from_p,
                                  const char *patch_p,
                                  const char *to_p)
{
    struct detools_apply_patch_t apply_patch;
    struct rwer_t rwer;
    const uint8_t *patch_buf_p;
    size_t patch_size;
    size_t patch_offset;
    size_t chunk_size;
    int res;

    rwer_init(&rwer, from_p, to_p);
    patch_buf_p = patch_init(patch_p, &patch_size);

    res = detools_apply_patch_init(&apply_patch,
                                   rwer_read,
                                   rwer_seek,
                                   rwer_write,
                                   &rwer);

    if (res != 0) {
        return (res);
    }

    /* Process up to 512 new patch bytes per iteration. */
    patch_offset = 0;

    while (patch_offset < patch_size) {
        chunk_size = MIN(patch_size - patch_offset, 512);

        res = detools_apply_patch_process(&apply_patch,
                                          &patch_buf_p[patch_offset],
                                          chunk_size);

        if (res < 0) {
            return (res);
        }

        patch_offset += (size_t)res;
    }

    res = detools_apply_patch_finalize(&apply_patch);

    if (res != 0) {
        return (res);
    }

    if (fclose(rwer.fto_p) != 0) {
        res = -1;
    }

    return (res);
}

int detools_apply_patch_callbacks(detools_read_t from_read,
                                  detools_read_t patch_read,
                                  detools_write_t to_write,
                                  void *arg_p)
{
    (void)from_read;
    (void)patch_read;
    (void)to_write;
    (void)arg_p;

    return (-DETOOLS_NOT_IMPLEMENTED);
}

int detools_apply_patch_init(struct detools_apply_patch_t *self_p,
                             detools_read_t from_read,
                             detools_seek_t from_seek,
                             detools_write_t to_write,
                             void *arg_p)
{
    self_p->from_read = from_read;
    self_p->from_seek = from_seek;
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

    switch (self_p->patch_type) {

    case PATCH_TYPE_NONE:
        res = apply_patch_none(self_p, patch_p, size);
        break;

    case PATCH_TYPE_NORMAL:
        res = apply_patch_normal(self_p, patch_p, size);
        break;

    case PATCH_TYPE_IN_PLACE:
        res = apply_patch_in_place(self_p, patch_p, size);
        break;

    default:
        res = -DETOOLS_INTERNAL_ERROR;
        break;
    }

    return (res);
}

int detools_apply_patch_finalize(struct detools_apply_patch_t *self_p)
{
    int res;

    do {
        res = detools_apply_patch_process(self_p, NULL, 0);
    } while (res == 0);

    if (res == -DETOOLS_ALREADY_DONE) {
        res = 0;
    }

    return (res);
}
