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

#include "detools.h"

#define PATCH_TYPE_NONE                                    -1
#define PATCH_TYPE_NORMAL                                   0
#define PATCH_TYPE_IN_PLACE                                 1

#define COMPRESSION_NONE                                    0
#define COMPRESSION_LZMA                                    1
#define COMPRESSION_CRLE                                    2

#define STATE_DIFF_SIZE                                     0
#define STATE_DIFF_DATA                                     1
#define STATE_EXTRA_SIZE                                    2
#define STATE_EXTRA_DATA                                    3
#define STATE_ADJUSTMENT                                    4
#define STATE_DONE                                          5

/**
 * @return Number of consumed patch bytes, or negative error code.
 */
static int read_header_common(struct detools_apply_patch_t *self_p,
                              const uint8_t *patch_p,
                              size_t size)
{
    int res;
    int patch_type;

    if (size < 1) {
        return (0);
    }

    patch_type = ((patch_p[0] >> 4) & 0x7);

    switch (patch_type) {

    case PATCH_TYPE_NORMAL:
        self_p->patch_type = patch_type;
        self_p->compression = (patch_p[0] & 0xf);
        init_normal(self_p);
        res = 1;
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
static int process_normal(struct detools_apply_patch_t *self_p,
                          const uint8_t *patch_p,
                          size_t patch_size,
                          uint8_t *to_p,
                          size_t *to_size_p)
{
    int i;
    uint8_t from[128];
    size_t size;

    switch (self_p->state) {

    case STATE_DIFF_SIZE:
        res = unpack_size(&size);

        if (res <= 0) {
            return (res);
        }

        self_p->state = STATE_DIFF_DATA;

        break;

    case STATE_DIFF_DATA:
        if (self_p->normal.to_pos + size > self_p->normal.to_size) {
            return (-1);
        }

        if (size > *to_size_p) {
            return (-1);
        }

        res = patch_reader_decompress(patch_p, patch_size, to_p, size);

        if (res < 0) {
            return (res);
        }

        read_res = read(&from[0], size);

        if (read_res != size) {
            return (-1);
        }

        for (i = 0; i < size; i++) {
            to_p[i] += from[i];
        }

        *to_size_p = size;
        self_p->normal.to_pos += size;

        if (self_p->normal.to_pos == self_p->normal.chunk_end) {
            self_p->state = STATE_EXTRA_SIZE;
        }

        break;

    case STATE_EXTRA_SIZE:
        res = unpack_size(&size);

        if (res <= 0) {
            return (res);
        }

        self_p->state = STATE_EXTRA_DATA;

        break;

    case STATE_EXTRA_DATA:
        if (to_pos + size <= to_size) {
            res = patch_reader_decompress(to_p, to_size_p);
        } else {
            res = -1;
        }

        if (self_p->normal.to_pos == self_p->normal.chunk_end) {
            self_p->state = STATE_ADJUSTMENT;
        }

        break;

    case STATE_ADJUSTMENT:
        seek(size);

        if (self_p->normal.to_pos == self_p->normal.to_size) {
            self_p->state = STATE_DONE;
        }

        break;

    default:
        res = -1;
        break;
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
    int write_res;
    uint8_t to[128];
    size_t to_size;

    res = 0;

    if (self_p->normal.to_size == -1) {
        res = unpack_size(patch_p, size, *self_p->to_size);
    } else {
        to_size = sizeof(to);
        res = process_normal(self_p, patch_p, size, &to[0], &to_size);

        if (res >= 0) {
            write_res = self_p->to_write(self_p->arg_p, &to[0], to_size);

            if (write_res < 0) {
                res = write_res;
            }
        }
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
                             detools_write_t to_write,
                             void *arg_p)
{
    self_p->from_read = from_read;
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
