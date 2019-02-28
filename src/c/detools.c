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

static int read_header_common(struct detools_apply_patch_t *self_p,
                              const uint8_t *patch_p,
                              size_t size)
{
    if (size < 1) {
        return (-1);
    }

    self_p->patch_type = ((patch_p[0] >> 4) & 0x7);
    self_p->compression = (patch_p[0] & 0xf);

    return (1);
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

static int apply_patch_normal(struct detools_apply_patch_t *self_p,
                              const uint8_t *patch_p,
                              size_t size)
{
    (void)self_p;
    (void)patch_p;

    if (size < 8) {
        return (0);
    }

    return (-1);
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

int detools_apply_patch_file_descriptors(int from,
                                         int patch,
                                         int to)
{
    (void)from;
    (void)patch;
    (void)to;

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

int detools_apply_patch_buffers(const uint8_t *from_p,
                                size_t from_size,
                                const uint8_t *patch_p,
                                size_t patch_size,
                                uint8_t *to_p,
                                size_t to_size)
{
    (void)from_p;
    (void)from_size;
    (void)patch_p;
    (void)patch_size;
    (void)to_p;
    (void)to_size;

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

    if (self_p->patch_type == PATCH_TYPE_NONE) {
        res = read_header_common(self_p, patch_p, size);
    } else if (self_p->patch_type == PATCH_TYPE_NORMAL) {
        res = apply_patch_normal(self_p, patch_p, size);
    } else if (self_p->patch_type == PATCH_TYPE_IN_PLACE) {
        res = apply_patch_in_place(self_p, patch_p, size);
    } else {
        res = -1;
    }

    return (res);
}

int detools_apply_patch_finalize(struct detools_apply_patch_t *self_p)
{
    (void)self_p;

    return (-1);
}
