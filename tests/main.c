#include <assert.h>
#include "../src/c/detools.h"

#define MIN(a, b) ((a) < (b) ? (a) : (b))

struct reader_t {
    int dummy;
};

static void reader_init(struct reader_t *self_p, const char *from_p)
{
    (void)self_p;
    (void)from_p;
}

static int reader_read(void *arg_p, uint8_t *buf_p, size_t size)
{
    (void)arg_p;
    (void)buf_p;
    (void)size;

    return (-1);
}

static uint8_t *patch_init(const char *patch_p, size_t *patch_size_p)
{
    (void)patch_p;
    (void)patch_size_p;

    return (NULL);
}

static uint8_t *to_init(const char *to_p,
                        const uint8_t **expected_to_pp,
                        size_t *to_size_p)
{
    (void)to_p;
    (void)expected_to_pp;

    *to_size_p = 0;

    return (NULL);
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

    actual_fto_p = fopen(actual_to_p, "rb");
    assert(actual_fto_p != NULL);
    expected_fto_p = fopen(to_p, "rb");
    assert(expected_fto_p != NULL);

    do {
        actual_byte = getc(actual_fto_p);
        expected_byte = getc(expected_fto_p);
        assert(actual_byte == expected_byte);
    } while (actual_byte != EOF);
}

static void test_apply_patch_foo(void)
{
    assert_apply_patch("tests/files/foo.old",
                       "tests/files/foo.patch",
                       "tests/files/foo.new");
}

static void test_apply_patch_foo_crle_compression_incremental(void)
{
    struct detools_apply_patch_t apply_patch;
    struct reader_t reader;
    const uint8_t *patch_p;
    uint8_t *to_p;
    const uint8_t *expected_to_p;
    size_t patch_size;
    size_t to_size;
    size_t expected_patch_size;
    size_t chunk_patch_size;
    size_t to_offset;
    size_t patch_offset;
    int res;
    size_t actual_to_size;

    reader_init(&reader, "tests/files/foo.old");
    patch_p = patch_init("tests/files/foo-crle.patch", &patch_size);
    to_p = to_init("tests/files/foo.new", &expected_to_p, &to_size);
    expected_patch_size = patch_size;

    assert(detools_apply_patch_init(&apply_patch,
                                    reader_read,
                                    &reader) == 0);

    /* Process up to 64 new patch bytes per iteration. */
    patch_offset = 0;
    to_offset = 0;
    actual_to_size = 0;

    while (patch_offset < expected_patch_size) {
        patch_size = MIN(expected_patch_size - patch_offset, 64);
        chunk_patch_size = patch_size;

        res = detools_apply_patch_process(&apply_patch,
                                          &patch_p[patch_offset],
                                          &patch_size,
                                          &to_p[to_offset],
                                          to_size - to_offset);

        assert(res >= 0);
        assert(patch_size <= chunk_patch_size);
        actual_to_size += (size_t)res;
        to_offset += (size_t)res;
        patch_offset += patch_size;
    }

    assert(actual_to_size == to_size);
    assert(memcmp(to_p, expected_to_p, to_size) == 0);

    assert(detools_apply_patch_flush(&apply_patch) == 0);
}

int main()
{
    test_apply_patch_foo();
    test_apply_patch_foo_crle_compression_incremental();

    return (0);
}
