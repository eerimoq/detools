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
    printf("size byte: 0x%02x\n", byte);
    size--;
    is_signed = ((byte & 0x40) == 0x40);
    *size_p = (byte & 0x3f);
    offset = 6;

    while ((byte & 0x80) != 0) {
        if (size == 0) {
            return (0);
        }

        byte = *buf_p++;
        printf("size byte: 0x%02x\n", byte);
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

    return (-1);
}

static int patch_reader_lzma_init(struct detools_apply_patch_patch_reader_t *self_p)
{
    lzma_ret ret;
    struct detools_apply_patch_patch_reader_lzma_t *lzma_p;

    lzma_p = &self_p->compression.lzma;
    memset(&lzma_p->stream, 0, sizeof(lzma_p->stream));

    ret = lzma_alone_decoder(&lzma_p->stream, UINT64_MAX);

    if (ret != LZMA_OK) {
        return (-1);
    }

    self_p->decompress = patch_reader_lzma_decompress;

    printf("lzma decompression init ok.\n");

    return (0);
}

static int patch_reader_crle_init(struct detools_apply_patch_patch_reader_t *self_p)
{
    (void)self_p;

    return (-1);
}

static int get_decompressed_data(lzma_stream *stream_p,
                                 uint8_t *buf_p,
                                 size_t size)
{
    int res;

    if (stream_p->avail_out >= size) {
        memcpy(buf_p, stream_p->next_out, size);
        stream_p->next_out += size;
        stream_p->avail_out -= size;
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
        return (-1);
    }

    if (lzma_p->stream.next_in != NULL) {
        memcpy(next_p, lzma_p->stream.next_in, lzma_p->stream.avail_in);
        free(lzma_p->next_in_p);
    }

    lzma_p->next_in_p = next_p;
    memcpy(&lzma_p->next_in_p[lzma_p->stream.avail_in],
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
    uint8_t *next_p;

    lzma_p = &self_p->compression.lzma;

    next_p = malloc(size);

    if (next_p == NULL) {
        return (-1);
    }

    if (lzma_p->stream.next_out != NULL) {
        memcpy(lzma_p->next_out_p,
               lzma_p->stream.next_out,
               lzma_p->stream.avail_out);
        free(lzma_p->next_out_p);
    }

    lzma_p->stream.next_out = next_p;

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

    lzma_p = &self_p->compression.lzma;

    /* Check if enough decompressed data is available. */
    res = get_decompressed_data(&lzma_p->stream, buf_p, size);

    if (res == 0) {
        return (res);
    }

    /* Decompress more data. */
    res = prepare_input_buffer(self_p);

    if (res != 0) {
        return (res);
    }

    res = prepare_output_buffer(self_p, size);

    if (res != 0) {
        return (res);
    }

    ret = lzma_code(&lzma_p->stream, LZMA_RUN);

    printf("avail out: %ld\n", lzma_p->stream.avail_out);

    if (ret != LZMA_OK) {
        return (-1);
    }

    return (get_decompressed_data(&lzma_p->stream, buf_p, size));
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
        res = -1;
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

static int patch_reader_unpack_size(struct detools_apply_patch_patch_reader_t *self_p,
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

    printf("size byte: 0x%02x\n", byte);
    is_signed = ((byte & 0x40) == 0x40);
    *size_p = (byte & 0x3f);
    offset = 6;

    while ((byte & 0x80) != 0) {
        res = patch_reader_decompress(self_p, &byte, 1);

        if (res != 0) {
            return (res);
        }

        printf("size byte: 0x%02x\n", byte);
        *size_p |= ((byte & 0x7f) << offset);
        offset += 7;
    }

    if (is_signed) {
        *size_p *= -1;
    }

    return ((offset - 6) / 7 + 1);
}

/**
 * @return Number of consumed patch bytes, or negative error code.
 */
static int apply_patch_none(struct detools_apply_patch_t *self_p,
                            const uint8_t *patch_p,
                            size_t size)
{
    int res;
    int res2;
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
        res = unpack_size(&patch_p[1], size - 1, &to_size);

        if (res > 0) {
            if (to_size > 0) {
                self_p->patch_type = patch_type;
                self_p->to_pos = 0;
                self_p->to_size = (size_t)to_size;
                self_p->state = STATE_DIFF_SIZE;
                res++;

                res2 = patch_reader_init(&self_p->patch_reader, compression);

                if (res2 != 0) {
                    res = res2;
                }
            } else {
                res = -1;
            }
        }

        break;

    default:
        res = -1;
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

    return (-1);
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

    printf("size: %d\n", size);

    if (self_p->to_pos + size > self_p->to_size) {
        return (-1);
    }

    self_p->state = next_state;
    self_p->chunk_pos = self_p->to_pos;
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
    int res2;
    int i;
    uint8_t to[128];
    size_t to_size;
    uint8_t from[128];

    printf("chunk_size: %d\n", self_p->chunk_size);

    to_size = MIN(sizeof(to), (size_t)self_p->chunk_size);

    res = patch_reader_decompress(&self_p->patch_reader,
                                  &to[0],
                                  to_size);

    if (res < 0) {
        return (res);
    }

    if (next_state == STATE_EXTRA_SIZE) {
        res2 = self_p->from_read(self_p->arg_p, &from[0], to_size);

        if (res2 != 0) {
            return (-1);
        }

        for (i = 0; i < (int)to_size; i++) {
            to[i] = (uint8_t)(to[i] + from[i]);
        }
    }

    self_p->to_pos += (int)to_size;

    if (self_p->to_pos == self_p->chunk_pos + self_p->chunk_size) {
        self_p->state = next_state;
    }

    res2 = self_p->to_write(self_p->arg_p, &to[0], to_size);

    if (res2 < 0) {
        return (res2);
    }

    return (res);
}

/**
 * @return Number of consumed patch bytes, or negative error code.
 */
static int process_normal_diff_size(struct detools_apply_patch_t *self_p)
{
    printf("diff size\n");
    return (process_normal_size(self_p, STATE_DIFF_DATA));
}

/**
 * @return Number of consumed patch bytes, or negative error code.
 */
static int process_normal_diff_data(struct detools_apply_patch_t *self_p)
{
    printf("diff data\n");
    return (process_normal_data(self_p, STATE_EXTRA_SIZE));
}

/**
 * @return Number of consumed patch bytes, or negative error code.
 */
static int process_normal_extra_size(struct detools_apply_patch_t *self_p)
{
    printf("extra size\n");
    return (process_normal_size(self_p, STATE_EXTRA_DATA));
}

/**
 * @return Number of consumed patch bytes, or negative error code.
 */
static int process_normal_extra_data(struct detools_apply_patch_t *self_p)
{
    printf("extra data\n");
    return (process_normal_data(self_p, STATE_ADJUSTMENT));
}

/**
 * @return Number of consumed patch bytes, or negative error code.
 */
static int process_normal_adjustment(struct detools_apply_patch_t *self_p)
{
    int res;
    int offset;

    printf("adjustment\n");
    res = patch_reader_unpack_size(&self_p->patch_reader, &offset);

    if (res <= 0) {
        return (res);
    }

    res = self_p->from_seek(self_p->arg_p, offset);

    if (res <= 0) {
        return (res);
    }

    if (self_p->to_pos == self_p->to_size) {
        self_p->state = STATE_DONE;
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

    default:
        res = -1;
        break;
    }

    if (res >= 0) {
        res = patch_reader_chunk_offset(&self_p->patch_reader);
    }

    return (res);
}

int detools_apply_patch_filenames(const char *from_p,
                                  const char *patch_p,
                                  const char *to_p)
{
    (void)from_p;
    (void)patch_p;
    (void)to_p;

    return (-1);
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

    return (-1);
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
        res = -1;
        break;
    }

    return (res);
}

int detools_apply_patch_finalize(struct detools_apply_patch_t *self_p)
{
    int res;

    if (self_p->state == STATE_DONE) {
        res = 0;
    } else {
        res = -1;
    }

    return (res);
}
