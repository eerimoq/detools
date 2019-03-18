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
#include <stdbool.h>

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
#define DETOOLS_SHORT_HEADER                   18
#define DETOOLS_NOT_ENOUGH_PATCH_DATA          19

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

/**
 * Memory read callback.
 *
 * @return zero(0) or negative error code.
 */
typedef int (*detools_mem_read_t)(void *arg_p,
                                  void *dst_p,
                                  uintptr_t src,
                                  size_t size);

/**
 * Memory write callback.
 *
 * @return zero(0) or negative error code.
 */
typedef int (*detools_mem_write_t)(void *arg_p,
                                   uintptr_t dst,
                                   void *src_p,
                                   size_t size);

/**
 * Memory erase callback.
 *
 * @return zero(0) or negative error code.
 */
typedef int (*detools_mem_erase_t)(void *arg_p, uintptr_t addr, size_t size);

struct detools_apply_patch_patch_reader_none_t {
    size_t patch_size;
    size_t patch_offset;
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

#define DETOOLS_CRLE_STATE_IDLE                              0
#define DETOOLS_CRLE_STATE_SCATTERED_SIZE                    1
#define DETOOLS_CRLE_STATE_SCATTERED_DATA                    2
#define DETOOLS_CRLE_STATE_REPEATED_REPETITIONS              3
#define DETOOLS_CRLE_STATE_REPEATED_DATA                     4
#define DETOOLS_CRLE_STATE_REPEATED_DATA_READ                5

struct detools_unpack_unsigned_size_t {
    int state;
    int value;
    int offset;
};

struct detools_apply_patch_patch_reader_crle_t {
    int state;
    union {
        struct {
            size_t number_of_bytes_left;
            struct detools_unpack_unsigned_size_t size;
        } scattered;
        struct {
            uint8_t value;
            size_t number_of_bytes_left;
            struct detools_unpack_unsigned_size_t size;
        } repeated;
    } kind;
};

struct detools_apply_patch_patch_reader_t {
    struct detools_apply_patch_t *apply_patch_p;
    struct {
        int state;
        int value;
        int offset;
        bool is_signed;
    } size;
    union {
#if DETOOLS_CONFIG_COMPRESSION_NONE == 1
        struct detools_apply_patch_patch_reader_none_t none;
#endif
#if DETOOLS_CONFIG_COMPRESSION_LZMA == 1
        struct detools_apply_patch_patch_reader_lzma_t lzma;
#endif
#if DETOOLS_CONFIG_COMPRESSION_CRLE == 1
        struct detools_apply_patch_patch_reader_crle_t crle;
#endif
    } compression;
    int (*destroy)(struct detools_apply_patch_patch_reader_t *self_p);
    int (*decompress)(struct detools_apply_patch_patch_reader_t *self_p,
                      uint8_t *buf_p,
                      size_t *size_p);
};

/**
 * The apply patch data structure.
 */
struct detools_apply_patch_t {
    detools_read_t from_read;
    detools_seek_t from_seek;
    size_t patch_size;
    detools_write_t to_write;
    void *arg_p;
    int patch_type;
    int state;
    size_t to_pos;
    size_t to_size;
    size_t chunk_size;
    struct detools_apply_patch_patch_reader_t patch_reader;
    struct {
        const uint8_t *buf_p;
        size_t size;
        size_t offset;
    } chunk;
};

/**
 * The in-place apply patch data structure.
 */
struct detools_apply_patch_in_place_t {
    detools_mem_read_t mem_read;
    detools_mem_write_t mem_write;
    detools_mem_erase_t mem_erase;
    size_t patch_size;
    void *arg_p;
    int patch_type;
    int state;
    size_t to_pos;
    size_t to_size;
    size_t chunk_size;
    struct detools_apply_patch_patch_reader_t patch_reader;
    struct {
        const uint8_t *buf_p;
        size_t size;
        size_t offset;
    } chunk;
};

/**
 * Initialize given apply patch object.
 *
 * @param[out] self_p Apply patch object to initialize.
 * @param[in] from_read Callback to read from-data.
 * @param[in] from_seek Callback to seek from current position in from-data.
 * @param[in] patch_size Patch size in bytes.
 * @param[in] to_write Destination callback.
 * @param[in] arg_p Argument passed to the callbacks.
 *
 * @return zero(0) or negative error code.
 */
int detools_apply_patch_init(struct detools_apply_patch_t *self_p,
                             detools_read_t from_read,
                             detools_seek_t from_seek,
                             size_t patch_size,
                             detools_write_t to_write,
                             void *arg_p);

/**
 * Call this function repeatedly until all patch data has been
 * processed or an error occurres. Call detools_apply_patch_finalize()
 * to finalize the patching, even if an error occurred.
 *
 * @param[in,out] self_p Initialized apply patch object.
 * @param[in] patch_p Next chunk of the patch.
 * @param[in] size Patch buffer size.
 *
 * @return zero(0) or negative error code.
 */
int detools_apply_patch_process(struct detools_apply_patch_t *self_p,
                                const uint8_t *patch_p,
                                size_t size);

/**
 * Call once after all data has been processed to finalize the
 * patching. The value returned from this function should be ignored
 * if an error occurred in detools_apply_patch_process().
 *
 * @param[in,out] self_p Initialized apply patch object.
 *
 * @return Size of to-data in bytes if the patch was applied
 *         successfully, or negative error code.
 */
int detools_apply_patch_finalize(struct detools_apply_patch_t *self_p);

/**
 * Initialize given in-place apply patch object.
 *
 * @param[out] self_p In-place apply patch object to initialize.
 * @param[in] mem_read Callback to read data.
 * @param[in] mem_write Callback to write data.
 * @param[in] mem_erase Callback to erase data.
 * @param[in] patch_size Patch size in bytes.
 * @param[in] arg_p Argument passed to the callbacks.
 *
 * @return zero(0) or negative error code.
 */
int detools_apply_patch_in_place_init(
    struct detools_apply_patch_in_place_t *self_p,
    detools_mem_read_t mem_read,
    detools_mem_write_t mem_write,
    detools_mem_erase_t mem_erase,
    size_t patch_size,
    void *arg_p);

/**
 * Call this function repeatedly until all patch data has been
 * processed or an error occurres. Call
 * detools_apply_patch_in_place_finalize() to finalize the patching,
 * even if an error occurred.
 *
 * @param[in,out] self_p Initialized apply patch object.
 * @param[in] patch_p Next chunk of the patch.
 * @param[in] size Patch buffer size.
 *
 * @return zero(0) or negative error code.
 */
int detools_apply_patch_in_place_process(
    struct detools_apply_patch_in_place_t *self_p,
    const uint8_t *patch_p,
    size_t size);

/**
 * Call once after all data has been processed to finalize the
 * patching. The value returned from this function should be ignored
 * if an error occurred in detools_apply_patch_in_place_process().
 *
 * @param[in,out] self_p Initialized apply patch object.
 *
 * @return Size of to-data in bytes if the patch was applied
 *         successfully, or negative error code.
 */
int detools_apply_patch_in_place_finalize(
    struct detools_apply_patch_in_place_t *self_p);

/**
 * Apply given patch using read, write and seek callbacks.
 *
 * @param[in] from_read Source read callback.
 * @param[in] from_seek Source seek callback.
 * @param[in] patch_read Patch read callback.
 * @param[in] patch_size Patch size in bytes.
 * @param[in] to_write Destination write callback.
 * @param[in] arg_p Argument passed to all callbacks.
 *
 * @return Size of to-data in bytes or negative error code.
 */
int detools_apply_patch_callbacks(detools_read_t from_read,
                                  detools_seek_t from_seek,
                                  detools_read_t patch_read,
                                  size_t patch_size,
                                  detools_write_t to_write,
                                  void *arg_p);

/**
 * Apply given in-place patch using read, write and erase callbacks.
 *
 * @param[in] mem_read Callback to read data.
 * @param[in] mem_write Callback to write data.
 * @param[in] mem_erase Callback to erase data.
 * @param[in] patch_read Patch read callback.
 * @param[in] patch_size Patch size in bytes.
 * @param[in] arg_p Argument passed to the callbacks.
 *
 * @return Size of to-data in bytes or negative error code.
 */
int detools_apply_patch_in_place_callbacks(detools_mem_read_t mem_read,
                                           detools_mem_write_t mem_write,
                                           detools_mem_erase_t mem_erase,
                                           detools_read_t patch_read,
                                           size_t patch_size,
                                           void *arg_p);

#if DETOOLS_CONFIG_FILE_IO == 1

/**
 * Apply given patch file to given from file and write the output to
 * given to file.
 *
 * @param[in] from_p Source file name.
 * @param[in] patch_p Patch file name.
 * @param[in] to_p Destination file name.
 *
 * @return Size of to-data in bytes or negative error code.
 */
int detools_apply_patch_filenames(const char *from_p,
                                  const char *patch_p,
                                  const char *to_p);

/**
 * Apply given patch file to given memory file.
 *
 * @param[in] memory_p Memory file name.
 * @param[in] patch_p Patch file name.
 *
 * @return Size of to-data in bytes or negative error code.
 */
int detools_apply_patch_in_place_filenames(const char *memory_p,
                                           const char *patch_p);

#endif

/**
 * Get the error string for given error code.
 *
 * @param[in] Error code.
 *
 * @return Error string, or NULL.
 */
const char *detools_error_as_string(int error);

#endif
