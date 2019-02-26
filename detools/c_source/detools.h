/**
 * BSD 2-Clause License
 *
 * Copyright (c) 2019, Erik Moqvist
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *
 * * Redistributions of source code must retain the above copyright notice, this
 *   list of conditions and the following disclaimer.
 *
 * * Redistributions in binary form must reproduce the above copyright notice,
 *   this list of conditions and the following disclaimer in the documentation
 *   and/or other materials provided with the distribution.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
 * FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 * SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
 * CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
 * OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

#ifndef DETOOLS_H
#define DETOOLS_H

#include <stdint.h>

/**
 * Read callback.
 */
typedef int (*detools_read_t)(void *arg_p, uint8_t *buf_p, size_t size);

/**
 * Write callback.
 */
typedef int (*detools_write_t)(void *arg_p, const uint8_t *buf_p, size_t size);

/**
 * The apply patch data structure.
 */
struct detools_apply_patch_t {
    detools_read_t from_read;
    void *arg_p;
};

/**
 * Apply given patch with file names.
 *
 * @param[in] from_read Destination buffer for output.
 * @param[in] patch_read Destination buffer for output.
 * @param[in] to_write Destination buffer for output.
 * @param[in] arg_p Destination buffer for output.
 *
 * @return zero(0) or negative error code.
 */
int detools_apply_patch_filenames(const char *from_p,
                                  const char *patch_p,
                                  const char *to_p);

/**
 * Apply given patch with file descriptors.
 *
 * @param[in] from_read Destination buffer for output.
 * @param[in] patch_read Destination buffer for output.
 * @param[in] to_write Destination buffer for output.
 * @param[in] arg_p Destination buffer for output.
 *
 * @return zero(0) or negative error code.
 */
int detools_apply_patch_file_descriptors(int from,
                                         int patch,
                                         int to);

/**
 * Apply given patch with callbacks.
 *
 * @param[in] from_read Destination buffer for output.
 * @param[in] patch_read Destination buffer for output.
 * @param[in] to_write Destination buffer for output.
 * @param[in] arg_p Destination buffer for output.
 *
 * @return zero(0) or negative error code.
 */
int detools_apply_patch_callbacks(detools_read_t from_read,
                                  detools_read_t patch_read,
                                  detools_write_t to_write,
                                  void *arg_p);

/**
 * Apply given patch with buffers.
 *
 * @param[in] from_read Destination buffer for output.
 * @param[in] patch_read Destination buffer for output.
 * @param[in] to_write Destination buffer for output.
 * @param[in] arg_p Destination buffer for output.
 *
 * @return zero(0) or negative error code.
 */
int detools_apply_patch_buffers(const uint8_t *from_p,
                                size_t from_size,
                                const uint8_t *patch_p,
                                size_t patch_size,
                                uint8_t *to_p,
                                size_t to_size);

/**
 * Initialize the apply patch object.
 *
 * @return zero(0) or negative error code.
 */
int detools_apply_patch_init(struct detools_apply_patch_t *self_p,
                             detools_read_t from_read,
                             void *arg_p);

/**
 * Feed data into the patcher and at the same time generate patched
 * output, ready to be written to disk/flash.
 *
 * @param[out] to_p Destination buffer for output.
 * @param[in] to_size Destination buffer size.
 * @param[in] patch_p Next chunk of the patch.
 * @param[in,out] patch_size_p Patch buffer size. Number of consumed
 *                             bytes on return.
 *
 * @return Zero or more number of bytes written to the destination
 *         buffer or -EEOF once the whole patch has been applied or
 *         -ENEEDSINPUT if more input is needed.
 */
int detools_apply_patch_process(struct detools_apply_patch_t *self_p,
                                uint8_t *to_p,
                                size_t to_size,
                                const uint8_t *patch_p,
                                size_t *patch_size_p);

/**
 * Feed data into the patcher and at the same time generate patched
 * output, ready to be written to disk/flash.
 *
 * @param[out] to_p Destination buffer for output.
 * @param[in] to_size Destination buffer size.
 * @param[in] patch_p Next chunk of the patch.
 * @param[in,out] patch_size_p Patch buffer size. Number of consumed
 *                             bytes on return.
 *
 * @return Zero or more number of bytes written to the destination
 *         buffer or -EEOF once the whole patch has been applied or
 *         -ENEEDSINPUT if more input is needed.
 */
int detools_apply_patch_flush(struct detools_apply_patch_t *self_p);

#endif
