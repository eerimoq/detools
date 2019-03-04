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

/*
 * Configuration.
 *
 * Define any of the defines below to 0 to disable given feature.
 */

#ifndef DETOOLS_CONFIG_FILE_IO
#    define DETOOLS_CONFIG_FILE_IO              1
#endif

#ifndef DETOOLS_CONFIG_COMPRESSION_NONE
#    define DETOOLS_CONFIG_COMPRESSION_NONE     1
#endif

#ifndef DETOOLS_CONFIG_COMPRESSION_LZMA
#    define DETOOLS_CONFIG_COMPRESSION_LZMA     1
#endif

#ifndef DETOOLS_CONFIG_COMPRESSION_CRLE
#    define DETOOLS_CONFIG_COMPRESSION_CRLE     1
#endif

#include <stdint.h>
#include <string.h>
#include <stdio.h>

/* Error codes. */
#define DETOOLS_OK                              0
#define DETOOLS_NOT_IMPLEMENTED                 1
#define DETOOLS_NOT_DONE                        2
#define DETOOLS_BAD_PATCH_TYPE                  3
#define DETOOLS_BAD_COMPRESSION                 4
#define DETOOLS_INTERNAL_ERROR                  5
#define DETOOLS_LZMA_INIT                       6
#define DETOOLS_LZMA_DECODE                     7
#define DETOOLS_OUT_OF_MEMORY                   8
#define DETOOLS_CORRUPT_PATCH                   9
#define DETOOLS_IO_FAILED                      10
#define DETOOLS_ALREADY_DONE                   11
#define DETOOLS_FILE_OPEN_FAILED               12
#define DETOOLS_FILE_CLOSE_FAILED              13
#define DETOOLS_FILE_READ_FAILED               14
#define DETOOLS_FILE_WRITE_FAILED              15
#define DETOOLS_FILE_SEEK_FAILED               16
#define DETOOLS_FILE_TELL_FAILED               17

/**
 * Read callback.
 *
 * @param[in] arg_p User data passed to detools_apply_patch_init().
 * @param[out] buf_p Buffer to read into.
 * @param[in] size Number of bytes to read.
 *
 * @return zero(0) or negative error code.
 */
typedef int (*detools_read_t)(void *arg_p, uint8_t *buf_p, size_t size);

/**
 * Write callback.
 *
 * @param[in] arg_p User data passed to detools_apply_patch_init().
 * @param[in] buf_p Buffer to write.
 * @param[in] size Number of bytes to write.
 *
 * @return zero(0) or negative error code.
 */
typedef int (*detools_write_t)(void *arg_p, const uint8_t *buf_p, size_t size);

/**
 * Seek from current position callback.
 *
 * @param[in] arg_p User data passed to detools_apply_patch_init().
 * @param[in] offset Offset to seek to from current position.
 *
 * @return zero(0) or negative error code.
 */
typedef int (*detools_seek_t)(void *arg_p, int offset);

struct detools_apply_patch_patch_reader_none_t {
    struct {
        const uint8_t *buf_p;
        size_t size;
        size_t offset;
    } chunk;
};

#if DETOOLS_CONFIG_COMPRESSION_LZMA == 1

#include <lzma.h>

struct detools_apply_patch_patch_reader_lzma_t {
    lzma_stream stream;
    uint8_t *input_p;
    uint8_t *output_p;
    size_t output_size;
};

#endif

struct detools_apply_patch_patch_reader_t {
    struct {
        const uint8_t *buf_p;
        size_t size;
        size_t offset;
    } chunk;
    union {
#if DETOOLS_CONFIG_COMPRESSION_NONE == 1
        struct detools_apply_patch_patch_reader_none_t none;
#endif
#if DETOOLS_CONFIG_COMPRESSION_LZMA == 1
        struct detools_apply_patch_patch_reader_lzma_t lzma;
#endif
    } compression;
    int (*decompress)(struct detools_apply_patch_patch_reader_t *self_p,
                      uint8_t *buf_p,
                      size_t size);
};

/**
 * The apply patch data structure.
 */
struct detools_apply_patch_t {
    detools_read_t from_read;
    detools_seek_t from_seek;
    detools_write_t to_write;
    void *arg_p;
    int patch_type;
    int to_pos;
    int to_size;
    int state;
    int chunk_size;
    struct detools_apply_patch_patch_reader_t patch_reader;
};

/**
 * Initialize given apply patch object.
 *
 * @param[out] self_p Apply patch object to initialize.
 * @param[in] from_read Callback to read from-data.
 * @param[in] from_seek Callback to seek from current position in from-data.
 * @param[in] to_write Destination callback.
 * @param[in] arg_p Argument passed to the callbacks.
 *
 * @return zero(0) or negative error code.
 */
int detools_apply_patch_init(struct detools_apply_patch_t *self_p,
                             detools_read_t from_read,
                             detools_seek_t from_seek,
                             detools_write_t to_write,
                             void *arg_p);

/**
 * Call this function repeatedly until all patch data has been
 * processed or an error occurres. Call detools_apply_patch_finalize()
 * to finalize the patching if no error occurred.
 *
 * @param[in,out] self_p Initialized apply patch object.
 * @param[in] patch_p Next chunk of the patch.
 * @param[in] size Patch buffer size.
 *
 * @return Zero or more number of consumed patch bytes, or negative
 *         error code.
 */
int detools_apply_patch_process(struct detools_apply_patch_t *self_p,
                                const uint8_t *patch_p,
                                size_t size);

/**
 * Call once after all data has been processed to finalize the
 * patching.
 *
 * @param[in,out] self_p Initialized apply patch object.
 *
 * @return zero(0) if the patch was applied successfully, or negative
 *         error code.
 */
int detools_apply_patch_finalize(struct detools_apply_patch_t *self_p);

#if DETOOLS_CONFIG_FILE_IO == 1

/**
 * Apply given patch file to given from file and write the output to
 * given to file.
 *
 * @param[in] from_p Source file name.
 * @param[in] patch_p Patch file name.
 * @param[in] to_p Destination file name.
 *
 * @return zero(0) or negative error code.
 */
int detools_apply_patch_filenames(const char *from_p,
                                  const char *patch_p,
                                  const char *to_p);

#endif

/**
 * Apply given patch using read and write callbacks.
 *
 * @param[in] from_read Source callback.
 * @param[in] patch_read Patch callback.
 * @param[in] to_write Destination callback.
 * @param[in] arg_p Argument passed to callbacks.
 *
 * @return zero(0) or negative error code.
 */
int detools_apply_patch_callbacks(detools_read_t from_read,
                                  detools_read_t patch_read,
                                  detools_write_t to_write,
                                  void *arg_p);

/**
 * Get the error string for given error code.
 *
 * @param[in] Error code.
 *
 * @return Error string, or NULL.
 */
const char *detools_error_as_string(int error);

#endif
