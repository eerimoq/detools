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

static int unpack_size(const uint8_t *buf_p, size_t size, int *size_p)
{
    uint8_t byte;
    bool is_signed;
    int offset;

    if (size == 0) {
        return (0);
    }

    byte = *buf_p++;
    printf("byte: 0x%02x\n", byte);
    size--;
    is_signed = ((byte & 0x40) == 0x40);
    *size_p = (byte & 0x3f);
    offset = 6;

    while ((byte & 0x80) != 0) {
        if (size == 0) {
            return (0);
        }

        byte = *buf_p++;
        printf("byte: 0x%02x\n", byte);
        size--;
        *size_p |= ((byte & 0x7f) << offset);
        offset += 7;
    }

    if (is_signed) {
        *size_p *= -1;
    }

    return ((offset - 6) / 7 + 1);
}

static void patch_reader_init(struct detools_apply_patch_patch_reader_t *self_p)
{
    (void)self_p;
}

/**
 * @return Number of consumed patch bytes, or negative error code.
 */
static int read_header_common(struct detools_apply_patch_t *self_p,
                              const uint8_t *patch_p,
                              size_t size)
{
    int res;
    int patch_type;
    int to_size;

    if (size < 1) {
        return (0);
    }

    patch_type = ((patch_p[0] >> 4) & 0x7);

    switch (patch_type) {

    case PATCH_TYPE_NORMAL:
        res = unpack_size(&patch_p[1], size - 1, &to_size);

        if (res > 0) {
            if (to_size > 0) {
                self_p->patch_type = patch_type;
                self_p->compression = (patch_p[0] & 0xf);
                self_p->to_pos = 0;
                self_p->to_size = (size_t)to_size;
                self_p->state = STATE_DIFF_SIZE;
                patch_reader_init(&self_p->patch_reader);
                res++;
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

static int patch_reader_decompress(struct detools_apply_patch_patch_reader_t *self_p,
                                   const uint8_t *patch_p,
                                   size_t patch_size,
                                   uint8_t *to_p,
                                   size_t *to_size_p)
{
    (void)self_p;
    (void)patch_p;
    (void)patch_size;
    (void)to_p;
    (void)to_size_p;

    return (-1);
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
                               const uint8_t *patch_p,
                               size_t patch_size,
                               int next_state)
{
    int res;
    int size;

    res = unpack_size(patch_p, patch_size, &size);

    if (res <= 0) {
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
                               const uint8_t *patch_p,
                               size_t patch_size,
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
                                  patch_p,
                                  patch_size,
                                  &to[0],
                                  &to_size);

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
static int process_normal_diff_size(struct detools_apply_patch_t *self_p,
                                    const uint8_t *patch_p,
                                    size_t patch_size)
{
    return (process_normal_size(self_p, patch_p, patch_size, STATE_DIFF_DATA));
}

/**
 * @return Number of consumed patch bytes, or negative error code.
 */
static int process_normal_diff_data(struct detools_apply_patch_t *self_p,
                                    const uint8_t *patch_p,
                                    size_t patch_size)
{
    return (process_normal_data(self_p, patch_p, patch_size, STATE_EXTRA_SIZE));
}

/**
 * @return Number of consumed patch bytes, or negative error code.
 */
static int process_normal_extra_size(struct detools_apply_patch_t *self_p,
                                     const uint8_t *patch_p,
                                     size_t patch_size)
{
    return (process_normal_size(self_p, patch_p, patch_size, STATE_EXTRA_DATA));
}

/**
 * @return Number of consumed patch bytes, or negative error code.
 */
static int process_normal_extra_data(struct detools_apply_patch_t *self_p,
                                     const uint8_t *patch_p,
                                     size_t patch_size)
{
    return (process_normal_data(self_p, patch_p, patch_size, STATE_ADJUSTMENT));
}

/**
 * @return Number of consumed patch bytes, or negative error code.
 */
static int process_normal_adjustment(struct detools_apply_patch_t *self_p,
                          const uint8_t *patch_p,
                          size_t patch_size)
{
    int res;
    int offset;

    res = unpack_size(patch_p, patch_size, &offset);

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

    switch (self_p->state) {

    case STATE_DIFF_SIZE:
        res = process_normal_diff_size(self_p, patch_p, size);
        break;

    case STATE_DIFF_DATA:
        res = process_normal_diff_data(self_p, patch_p, size);
        break;

    case STATE_EXTRA_SIZE:
        res = process_normal_extra_size(self_p, patch_p, size);
        break;

    case STATE_EXTRA_DATA:
        res = process_normal_extra_data(self_p, patch_p, size);
        break;

    case STATE_ADJUSTMENT:
        res = process_normal_adjustment(self_p, patch_p, size);
        break;

    default:
        res = -1;
        break;
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
        res = read_header_common(self_p, patch_p, size);
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
