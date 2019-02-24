#include <assert.h>
#include "detools.h"

struct reader_t {
};

static int reader_read(void *arg_p, uint8_t *buf_p, size_t size)
{
    int res;
    struct reader_t *reader_p;

    reader_p = arg_p;

    res = MIN(reader_p->left, size);

    if (res > 0) {
        memcpy(buf_p, reader_p->buf_p, res);
    }

    return (res);
}

static void test_crle_apply_patch_foo(void)
{
    struct detools_crle_apply_patch_t patcher;
    uint8_t *to_p;
    uint8_t *patch_p;
    size_t to_size;
    size_t patch_size;
    size_t expected_consumed_patch_size;
    struct reader_t reader;

    reader_init(&reader, "tests/files/foo.old");
    to_p = alloc("tests/files/foo.new", &to_size);
    patch_p = load("tests/files/foo.patch", &patch_size);
    expected_consumed_patch_size = patch_size;

    assert(detools_crle_apply_patch_init(&patcher,
                                         reader_read,
                                         &reader) == 0);

    assert(detools_crle_apply_patch_process(&patcher,
                                            &to_p[0],
                                            to_size,
                                            &patch_p[0],
                                            &patch_size) == to_size);
    assert(patch_size == expected_consumed_patch_size);
}

int main()
{
    test_crle_apply_patch();

    return (0);
}
