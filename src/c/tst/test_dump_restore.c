#include <stdlib.h>
#include "nala.h"
#include "utils.h"
#include "../detools.h"

static void init(struct detools_apply_patch_t *apply_patch_p,
                 size_t patch_size)
{
    int res;

    res = detools_apply_patch_init(apply_patch_p,
                                   utils_from_read,
                                   utils_from_seek,
                                   patch_size,
                                   utils_to_write,
                                   NULL);
    ASSERT_EQ(res, DETOOLS_OK);
}

static void dump(struct detools_apply_patch_t *apply_patch_p)
{
    int res;

    res = detools_apply_patch_dump(apply_patch_p, utils_state_write);
    ASSERT_EQ(res, DETOOLS_OK);
    ASSERT_EQ(fseek(utils_files.state.file_p, 0, SEEK_SET), 0);
}

static void restore(struct detools_apply_patch_t *apply_patch_p)
{
    int res;

    res = detools_apply_patch_restore(apply_patch_p, utils_state_read);
    ASSERT_EQ(res, DETOOLS_OK);
    ASSERT_EQ(fseek(utils_files.state.file_p, 0, SEEK_SET), 0);
}

static void process(struct detools_apply_patch_t *apply_patch_p,
                    const uint8_t *buf_p,
                    size_t size)
{
    int res;

    res = detools_apply_patch_process(apply_patch_p, buf_p, size);
    ASSERT_EQ(res, DETOOLS_OK);
}

static void finalize(struct detools_apply_patch_t *apply_patch_p,
                     size_t size)
{
    int res;

    res = detools_apply_patch_finalize(apply_patch_p);
    ASSERT_EQ(res, size);
}

TEST(foo_none_at_offset_0)
{
    struct detools_apply_patch_t apply_patch;

    utils_files_init("../../../tests/files/foo/old",
                     "../../../tests/files/foo/none.patch");

    /* Init and dump. */
    init(&apply_patch, utils_files.patch.size);
    dump(&apply_patch);

    /* Init again, restore and apply the patch. */
    init(&apply_patch, 0);
    restore(&apply_patch);
    process(&apply_patch, utils_files.patch.buf_p, utils_files.patch.size);
    finalize(&apply_patch, 2780);

    utils_files_destroy();
}

TEST(foo_none_at_offset_100_and_2791)
{
    struct detools_apply_patch_t apply_patch;

    utils_files_init("../../../tests/files/foo/old",
                     "../../../tests/files/foo/none.patch");

    /* Init, process 100 bytes and dump. */
    init(&apply_patch, utils_files.patch.size);
    process(&apply_patch, utils_files.patch.buf_p, 100);
    dump(&apply_patch);

    /* Init again, restore, apply all but one byte and dump again. */
    init(&apply_patch, 0);
    restore(&apply_patch);
    process(&apply_patch,
            &utils_files.patch.buf_p[100],
            utils_files.patch.size - 100 - 1);
    dump(&apply_patch);

    /* Init once again, restore and apply the last byte. */
    init(&apply_patch, 0);
    restore(&apply_patch);
    process(&apply_patch, &utils_files.patch.buf_p[utils_files.patch.size - 1], 1);
    finalize(&apply_patch, 2780);

    utils_files_destroy();
}

TEST(foo_none_dump_state_write_error)
{
    struct detools_apply_patch_t apply_patch;
    int res;

    utils_files_init("../../../tests/files/foo/old",
                     "../../../tests/files/foo/none.patch");

    init(&apply_patch, utils_files.patch.size);

    utils_state_write_mock_once(sizeof(apply_patch), -1);
    res = detools_apply_patch_dump(&apply_patch, utils_state_write);
    ASSERT_EQ(res, -DETOOLS_IO_FAILED);

    utils_files_destroy();
}
