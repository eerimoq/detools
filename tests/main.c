#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include "../src/c/detools.h"

#define MIN(a, b) ((a) < (b) ? (a) : (b))

struct rwer_t {
    FILE *ffrom_p;
    struct {
        uint8_t *actual_p;
        uint8_t *expected_p;
        size_t size;
        size_t written;
    } to;
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
    FILE *file_p;
    long size;

    self_p->ffrom_p = myfopen(from_p, "rb");

    file_p = myfopen(to_p, "rb");

    assert(fseek(file_p, 0, SEEK_END) == 0);
    size = ftell(file_p);
    assert(size > 0);
    self_p->to.size = (size_t)size;
    assert(fseek(file_p, 0, SEEK_SET) == 0);

    self_p->to.actual_p = mymalloc(self_p->to.size);
    self_p->to.expected_p = mymalloc(self_p->to.size);
    assert(fread(self_p->to.expected_p, self_p->to.size, 1, file_p) == 1);

    fclose(file_p);

    self_p->to.written = 0;
}

static void rwer_assert_to_ok(struct rwer_t *self_p)
{
    assert(self_p->to.written == self_p->to.size);
    assert(memcmp(self_p->to.actual_p,
                  self_p->to.expected_p,
                  self_p->to.size) == 0);
}

static int rwer_read(void *arg_p, uint8_t *buf_p, size_t size)
{
    struct rwer_t *self_p;

    self_p = (struct rwer_t *)arg_p;

    if (fread(buf_p, size, 1, self_p->ffrom_p) == 1) {
        return (0);
    } else {
        return (-1);
    }
}

static int rwer_seek(void *arg_p, int offset)
{
    struct rwer_t *self_p;

    self_p = (struct rwer_t *)arg_p;

    return (fseek(self_p->ffrom_p, offset, SEEK_CUR));
}

static int rwer_write(void *arg_p, const uint8_t *buf_p, size_t size)
{
    struct rwer_t *self_p;

    self_p = (struct rwer_t *)arg_p;

    assert(self_p->to.size - self_p->to.written >= size);

    memcpy(&self_p->to.actual_p[self_p->to.written], buf_p, size);
    self_p->to.written += size;

    return (0);
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

static void assert_apply_patch(const char *from_p,
                               const char *patch_p,
                               const char *to_p)
{
    const char *actual_to_p = "assert-apply-patch.new";
    FILE *actual_fto_p;
    FILE *expected_fto_p;
    int actual_byte;
    int expected_byte;

    assert(detools_apply_patch_filenames(from_p,
                                         patch_p,
                                         actual_to_p) == 0);

    actual_fto_p = myfopen(actual_to_p, "rb");
    expected_fto_p = myfopen(to_p, "rb");

    do {
        actual_byte = getc(actual_fto_p);
        expected_byte = getc(expected_fto_p);
        assert(actual_byte == expected_byte);
    } while (actual_byte != EOF);
}

static void assert_apply_patch_error(const char *from_p,
                                     const char *patch_p,
                                     int expected_res)
{
    const char *actual_to_p = "assert-apply-patch.new";

    assert(detools_apply_patch_filenames(from_p,
                                         patch_p,
                                         actual_to_p) == expected_res);
}

static void test_apply_patch_foo(void)
{
    assert_apply_patch("tests/files/foo.old",
                       "tests/files/foo.patch",
                       "tests/files/foo.new");
}

static void test_apply_patch_foo_backwards(void)
{
    assert_apply_patch("tests/files/foo.new",
                       "tests/files/foo-backwards.patch",
                       "tests/files/foo.old");
}

static void test_apply_patch_micropython(void)
{
    assert_apply_patch(
        "tests/files/micropython-esp8266-20180511-v1.9.4.bin",
        "tests/files/micropython-esp8266-20180511-v1.9.4--20190125-v1.10.patch",
        "tests/files/micropython-esp8266-20190125-v1.10.bin");
}

static void test_apply_patch_foo_none_compression(void)
{
    assert_apply_patch_error("tests/files/foo.old",
                             "tests/files/foo-none.patch",
                             -DETOOLS_NOT_IMPLEMENTED);
}

static void test_apply_patch_micropython_none_compression(void)
{
    assert_apply_patch_error(
        "tests/files/micropython-esp8266-20180511-v1.9.4.bin",
        "tests/files/micropython-esp8266-20180511-v1.9.4--20190125-v1.10-none.patch",
        -DETOOLS_NOT_IMPLEMENTED);
}

static void test_apply_patch_foo_crle_compression(void)
{
    assert_apply_patch_error("tests/files/foo.old",
                             "tests/files/foo-crle.patch",
                             -DETOOLS_NOT_IMPLEMENTED);
}

static void test_apply_patch_micropython_in_place(void)
{
    assert_apply_patch_error(
        "tests/files/micropython-esp8266-20180511-v1.9.4.bin",
        "tests/files/micropython-esp8266-20180511-v1.9.4--"
        "20190125-v1.10-in-place.patch",
        -DETOOLS_NOT_IMPLEMENTED);
}

static void test_apply_patch_foo_in_place_3000_1500(void)
{
    assert_apply_patch_error("tests/files/foo.old",
                             "tests/files/foo-in-place-3000-1500.patch",
                             -DETOOLS_NOT_IMPLEMENTED);
}

static void test_apply_patch_foo_bad_patch_type(void)
{
    assert_apply_patch_error("tests/files/foo.old",
                             "tests/files/foo-bad-patch-type.patch",
                             -DETOOLS_BAD_PATCH_TYPE);
}

static void test_apply_patch_foo_bad_compression(void)
{
    assert_apply_patch_error("tests/files/foo.old",
                             "tests/files/foo-bad-compression.patch",
                             -DETOOLS_BAD_COMPRESSION);
}

static void test_apply_patch_foo_compression_incremental(void)
{
    struct detools_apply_patch_t apply_patch;
    struct rwer_t rwer;
    const uint8_t *patch_p;
    size_t patch_size;
    size_t expected_patch_size;
    size_t patch_offset;
    int res;

    rwer_init(&rwer, "tests/files/foo.old", "tests/files/foo.new");
    patch_p = patch_init("tests/files/foo.patch", &patch_size);
    expected_patch_size = patch_size;

    assert(detools_apply_patch_init(&apply_patch,
                                    rwer_read,
                                    rwer_seek,
                                    rwer_write,
                                    &rwer) == 0);

    /* Process up to 64 new patch bytes per iteration. */
    patch_offset = 0;

    while (patch_offset < expected_patch_size) {
        patch_size = MIN(expected_patch_size - patch_offset, 64);
        res = detools_apply_patch_process(&apply_patch,
                                          &patch_p[patch_offset],
                                          patch_size);
        assert((res >= 0) && (res <= (int)patch_size));
        patch_offset += (size_t)res;
    }

    assert(detools_apply_patch_finalize(&apply_patch) == 0);
    rwer_assert_to_ok(&rwer);
}

int main()
{
    test_apply_patch_foo();
    test_apply_patch_foo_backwards();
    test_apply_patch_micropython();
    test_apply_patch_foo_none_compression();
    test_apply_patch_micropython_none_compression();
    test_apply_patch_foo_crle_compression();
    test_apply_patch_micropython_in_place();
    test_apply_patch_foo_in_place_3000_1500();
    test_apply_patch_foo_bad_patch_type();
    test_apply_patch_foo_bad_compression();

    test_apply_patch_foo_compression_incremental();

    return (0);
}
