/* #include <dbg.h> */
#include <dirent.h>
#include <sys/stat.h>
#include <sys/types.h>
#include "nala.h"
#include "../detools.h"

static const uint8_t from[256] = { 0, };

static void create_from_file(void)
{
    FILE *file_p;

    file_p = fopen("from", "wb");
    ASSERT_NE(file_p, NULL);
    ASSERT_EQ(fwrite(&from[0], sizeof(from), 1, file_p), 1);
    fclose(file_p);
}

static bool is_file(const char *path_p)
{
    struct stat statbuf;

    ASSERT_EQ(stat(path_p, &statbuf), 0);

    return (S_ISREG(statbuf.st_mode));
}

static void create_patch_file(const char *corpus_file_path_p)
{
    FILE *file_p;
    uint8_t size;
    uint8_t patch[256];

    /* Read corpus file. */
    file_p = fopen(corpus_file_path_p, "rb");
    ASSERT_NE(file_p, NULL);
    ASSERT_EQ(fread(&size, 1, 1, file_p), 1);

    if (size > 0) {
        ASSERT_EQ(fread(&patch[0], size, 1, file_p), 1);
        /* dbgh(&patch[0], size); */
    }

    fclose(file_p);

    /* Create patch file. */
    file_p = fopen("patch", "wb");
    ASSERT_NE(file_p, NULL);

    if (size > 0) {
        ASSERT_EQ(fwrite(&patch[0], size, 1, file_p), 1);
    }

    fclose(file_p);
}

TEST(all_ok)
{
    DIR *dir_p;
    struct dirent *item_p;
    char corpus_file_path[512];
    int res;

    dir_p = opendir("corpus");

    if (dir_p != NULL) {
        create_from_file();

        while ((item_p = readdir(dir_p)) != NULL) {
            sprintf(&corpus_file_path[0], "corpus/%s", item_p->d_name);

            if (!is_file(&corpus_file_path[0])) {
                continue;
            }

            printf("\n");
            printf("Corpus file:  '%s'\n", &corpus_file_path[0]);
            create_patch_file(&corpus_file_path[0]);
            res = detools_apply_patch_filenames("from", "patch", "to");
            printf("Patch result: %s (%d)\n", detools_error_as_string(res), res);
        }

        closedir(dir_p);
    }
}
