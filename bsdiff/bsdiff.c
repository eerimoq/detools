/*-
 * Copyright 2003-2005 Colin Percival
 * Copyright (c) 2019, Erik Moqvist
 * All rights reserved
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted providing that the following conditions
 * are met:
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 *
 * THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
 * IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
 * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
 * DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
 * OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
 * HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
 * STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING
 * IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 * POSSIBILITY OF SUCH DAMAGE.
 */

#include <sys/types.h>
#include <err.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <Python.h>

#define MIN(x, y) (((x) < (y)) ? (x) : (y))

static off_t matchlen(u_char *old_p,
                      off_t old_size,
                      u_char *new_p,
                      off_t new_size)
{
    off_t i;

    for (i = 0; i < MIN(old_size, new_size); i++) {
        if (old_p[i] != new_p[i]) {
            break;
        }
    }

    return (i);
}

static off_t search(off_t *i_p,
                    u_char *old_p,
                    off_t old_size,
                    u_char *new_p,
                    off_t new_size,
                    off_t st,
                    off_t en,
                    off_t *pos)
{
    off_t x;
    off_t y;

    if (en - st < 2) {
        x = matchlen(old_p + i_p[st], old_size - i_p[st], new_p, new_size);
        y = matchlen(old_p + i_p[en], old_size - i_p[en], new_p, new_size);

        if (x > y) {
            *pos = i_p[st];

            return (x);
        } else {
            *pos = i_p[en];

            return (y);
        }
    }

    x = (st + (en - st) / 2);

    if (memcmp(old_p + i_p[x], new_p, MIN(old_size - i_p[x], new_size)) < 0) {
        return search(i_p, old_p, old_size, new_p, new_size, x, en, pos);
    } else {
        return search(i_p, old_p, old_size, new_p, new_size, st, x, pos);
    }
}

static void pack_i64(u_char *buf_p, off_t x)
{
    buf_p[0] = (x >> 56);
    buf_p[1] = (x >> 48);
    buf_p[2] = (x >> 40);
    buf_p[3] = (x >> 32);
    buf_p[4] = (x >> 24);
    buf_p[5] = (x >> 16);
    buf_p[6] = (x >> 8);
    buf_p[7] = (x >> 0);
}

static int append_bytes(PyObject *list_p, u_char *buf_p, off_t size)
{
    int res;
    PyObject *bytes_p;

    bytes_p = PyBytes_FromStringAndSize((char *)buf_p, size);

    if (bytes_p == NULL) {
        return (-1);
    }

    res = PyList_Append(list_p, bytes_p);

    Py_DECREF(bytes_p);

    return (res);
}

static int append_size(PyObject *list_p, off_t size)
{
    u_char buf[8];

    pack_i64(&buf[0], size);

    return (append_bytes(list_p, &buf[0], sizeof(buf)));
}

static int append_buffer(PyObject *list_p, u_char *buf_p, off_t size)
{
    int res;

    res = append_size(list_p, size);

    if (res != 0) {
        return (res);
    }

    return (append_bytes(list_p, buf_p, size));
}

static int parse_args(PyObject *args_p,
                      Py_ssize_t *suffix_array_length_p,
                      off_t **i_pp,
                      char **old_pp,
                      char **new_pp,
                      Py_ssize_t *old_size_p,
                      Py_ssize_t *new_size_p)
{
    int res;
    PyObject *suffix_array_p;
    PyObject *old_bytes_p;
    PyObject *new_bytes_p;
    int i;

    res = PyArg_ParseTuple(args_p,
                           "OOO",
                           &suffix_array_p,
                           &old_bytes_p,
                           &new_bytes_p);

    if (res == 0) {
        return (-1);
    }

    *suffix_array_length_p = PyList_Size(suffix_array_p);

    if (*suffix_array_length_p <= 0) {
        return (-1);
    }

    *i_pp = PyMem_Malloc(*suffix_array_length_p * sizeof(**i_pp));

    if (*i_pp == NULL) {
        return (-1);
    }

    for (i = 0; i < *suffix_array_length_p; i++) {
        (*i_pp)[i] = PyLong_AsLong(PyList_GET_ITEM(suffix_array_p, i));
    }

    res = PyBytes_AsStringAndSize(old_bytes_p, old_pp, old_size_p);

    if (res != 0) {
        goto err1;
    }

    res = PyBytes_AsStringAndSize(new_bytes_p, new_pp, new_size_p);

    if (res != 0) {
        goto err1;
    }

    return (res);

 err1:
    PyMem_Free(*i_pp);

    return (-1);
}

static int create_patch_loop(PyObject *list_p,
                             off_t *i_p,
                             u_char *old_p,
                             Py_ssize_t old_size,
                             u_char *new_p,
                             Py_ssize_t new_size,
                             u_char *db_p,
                             u_char *eb_p)
{
    int res;
    off_t scan;
    off_t pos;
    off_t len;
    off_t last_scan;
    off_t last_pos;
    off_t last_offset;
    off_t old_score;
    off_t scsc;
    off_t s;
    off_t Sf;
    off_t lenf;
    off_t Sb;
    off_t lenb;
    off_t overlap;
    off_t Ss;
    off_t lens;
    off_t i;

    scan = 0;
    len = 0;
    last_scan = 0;
    last_pos = 0;
    last_offset = 0;
    pos = 0;

    while (scan < new_size) {
        old_score = 0;

        for (scsc = scan += len; scan < new_size; scan++) {
            len = search(i_p,
                         old_p,
                         old_size,
                         new_p + scan,
                         new_size - scan,
                         0,
                         old_size,
                         &pos);

            for (; scsc < scan + len; scsc++) {
                if ((scsc + last_offset < old_size)
                    && (old_p[scsc + last_offset] == new_p[scsc])) {
                    old_score++;
                }
            }

            if (((len == old_score) && (len != 0)) || (len > old_score + 8)) {
                break;
            }

            if ((scan + last_offset < old_size)
                && (old_p[scan + last_offset] == new_p[scan])) {
                old_score--;
            }
        }

        if ((len != old_score) || (scan == new_size)) {
            s = 0;
            Sf = 0;
            lenf = 0;

            for (i = 0; (last_scan + i < scan) && (last_pos + i < old_size);) {
                if (old_p[last_pos + i] == new_p[last_scan + i]) {
                    s++;
                }

                i++;

                if (s * 2 - i > Sf * 2 - lenf) {
                    Sf = s;
                    lenf = i;
                }
            }

            lenb = 0;

            if (scan < new_size) {
                s = 0;
                Sb = 0;

                for (i = 1; (scan >= last_scan + i) && (pos >= i); i++) {
                    if (old_p[pos - i] == new_p[scan - i]) {
                        s++;
                    }

                    if (s * 2 - i > Sb * 2 - lenb) {
                        Sb = s;
                        lenb = i;
                    }
                }
            }

            if (last_scan + lenf > scan - lenb) {
                overlap = (last_scan + lenf) - (scan - lenb);
                s = 0;
                Ss = 0;
                lens = 0;

                for (i = 0; i < overlap; i++) {
                    if (new_p[last_scan + lenf - overlap + i]
                        == old_p[last_pos + lenf - overlap + i]) {
                        s++;
                    }

                    if(new_p[scan - lenb + i] == old_p[pos - lenb + i]) {
                        s--;
                    }

                    if (s > Ss) {
                        Ss = s;
                        lens = (i + 1);
                    }
                }

                lenf += (lens - overlap);
                lenb -= lens;
            }

            for (i = 0; i < lenf; i++) {
                db_p[i] = (new_p[last_scan + i] - old_p[last_pos + i]);
            }

            for(i = 0; i < (scan - lenb) - (last_scan + lenf); i++) {
                eb_p[i] = new_p[last_scan + lenf + i];
            }

            /* Diff data. */
            res = append_buffer(list_p, &db_p[0], lenf);

            if (res != 0) {
                return (res);
            }

            /* Extra data. */
            res = append_buffer(list_p,
                                &eb_p[0],
                                (scan - lenb) - (last_scan + lenf));

            if (res != 0) {
                return (res);
            }

            /* Adjustment. */
            res = append_size(list_p, (pos - lenb) - (last_pos + lenf));

            if (res != 0) {
                return (res);
            }

            last_scan = (scan - lenb);
            last_pos = (pos - lenb);
            last_offset = (pos - scan);
        }
    }

    return (0);
}

static PyObject *create_patch(PyObject *self_p, PyObject *args_p)
{
    int res;
    u_char *old_p;
    u_char *new_p;
    Py_ssize_t old_size;
    Py_ssize_t new_size;
    off_t *i_p;
    u_char *db_p;
    u_char *eb_p;
    PyObject *list_p;
    Py_ssize_t suffix_array_length;

    res = parse_args(args_p,
                     &suffix_array_length,
                     &i_p,
                     (char **)&old_p,
                     (char **)&new_p,
                     &old_size,
                     &new_size);

    if (res != 0) {
        return (NULL);
    }

    list_p = PyList_New(0);

    if (list_p == NULL) {
        goto err1;
    }

    db_p = PyMem_Malloc(suffix_array_length * sizeof(*db_p));

    if (db_p == NULL) {
        goto err2;
    }

    eb_p = PyMem_Malloc(suffix_array_length * sizeof(*eb_p));

    if (eb_p == NULL) {
        goto err3;
    }

    res = create_patch_loop(list_p,
                            i_p,
                            old_p,
                            old_size,
                            new_p,
                            new_size,
                            db_p,
                            eb_p);

    if (res != 0) {
        goto err4;
    }

    PyMem_Free(eb_p);
    PyMem_Free(db_p);
    PyMem_Free(i_p);

    return (list_p);

 err4:
    PyMem_Free(eb_p);

 err3:
    PyMem_Free(db_p);

 err2:
    Py_DECREF(list_p);

 err1:
    PyMem_Free(i_p);

    return (NULL);
}

static PyMethodDef module_methods[] = {
    { "create_patch", create_patch, METH_VARARGS },
    { NULL }
};

static PyModuleDef module = {
    PyModuleDef_HEAD_INIT,
    .m_name = "_bsdiff",
    .m_doc = NULL,
    .m_size = -1,
    .m_methods = module_methods
};

PyMODINIT_FUNC PyInit__bsdiff(void)
{
    PyObject *m_p;

    /* Module creation. */
    m_p = PyModule_Create(&module);

    if (m_p == NULL) {
        return (NULL);
    }

    return (m_p);
}
